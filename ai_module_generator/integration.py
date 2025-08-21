"""
Odoo Integration Layer

Handles module packaging, installation, and updating in Odoo instances.
Provides API interface for interaction with Odoo backend.
"""

import os
import json
import requests
import xmlrpc.client
import logging
import shutil
import zipfile
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .nlp_parser import ModuleSpec


@dataclass
class OdooConnection:
    """Odoo connection configuration"""
    url: str
    database: str
    username: str
    password: str
    port: int = 8069
    protocol: str = "http"
    
    @property
    def full_url(self) -> str:
        return f"{self.protocol}://{self.url}:{self.port}"


class OdooIntegration:
    """
    Integration layer for communicating with Odoo instances.
    Handles module deployment, installation, and management.
    """
    
    def __init__(self, connection: Optional[OdooConnection] = None):
        """
        Initialize Odoo integration.
        
        Args:
            connection: Odoo connection configuration
        """
        self.connection = connection
        self.logger = logging.getLogger(__name__)
        self._uid = None
        self._common = None
        self._models = None
        
    def connect(self, connection: Optional[OdooConnection] = None) -> bool:
        """
        Establish connection to Odoo instance.
        
        Args:
            connection: Connection configuration (uses stored if not provided)
            
        Returns:
            True if connection successful, False otherwise
        """
        if connection:
            self.connection = connection
        
        if not self.connection:
            raise ValueError("No connection configuration provided")
        
        try:
            # Connect to common services
            common_url = f"{self.connection.full_url}/xmlrpc/2/common"
            self._common = xmlrpc.client.ServerProxy(common_url)
            
            # Authenticate
            self._uid = self._common.authenticate(
                self.connection.database,
                self.connection.username, 
                self.connection.password,
                {}
            )
            
            if not self._uid:
                self.logger.error("Authentication failed")
                return False
            
            # Connect to object services
            models_url = f"{self.connection.full_url}/xmlrpc/2/object"
            self._models = xmlrpc.client.ServerProxy(models_url)
            
            self.logger.info(f"Successfully connected to Odoo at {self.connection.full_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Odoo: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the connection to Odoo.
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            if not self._models or not self._uid:
                return False
            
            # Try a simple query
            version = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'search_read',
                [[['name', '=', 'base']]],
                {'fields': ['name', 'state'], 'limit': 1}
            )
            
            return len(version) > 0
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_installed_modules(self) -> List[Dict[str, Any]]:
        """
        Get list of installed modules.
        
        Returns:
            List of module information dictionaries
        """
        try:
            modules = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'search_read',
                [[['state', '=', 'installed']]],
                {'fields': ['name', 'display_name', 'version', 'summary']}
            )
            return modules
            
        except Exception as e:
            self.logger.error(f"Failed to get installed modules: {e}")
            return []
    
    def module_exists(self, module_name: str) -> bool:
        """
        Check if a module exists in the Odoo instance.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if module exists, False otherwise
        """
        try:
            modules = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'search',
                [[['name', '=', module_name]]]
            )
            return len(modules) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to check module existence: {e}")
            return False
    
    def get_module_info(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Module information dictionary or None if not found
        """
        try:
            modules = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'search_read',
                [[['name', '=', module_name]]],
                {'fields': ['name', 'display_name', 'version', 'state', 'summary', 'description']}
            )
            
            return modules[0] if modules else None
            
        except Exception as e:
            self.logger.error(f"Failed to get module info: {e}")
            return None
    
    def install_module(self, module_name: str) -> bool:
        """
        Install a module in Odoo.
        
        Args:
            module_name: Name of the module to install
            
        Returns:
            True if installation successful, False otherwise
        """
        try:
            # Find the module
            module_ids = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'search',
                [[['name', '=', module_name]]]
            )
            
            if not module_ids:
                self.logger.error(f"Module {module_name} not found")
                return False
            
            # Install the module
            self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'button_immediate_install',
                [module_ids]
            )
            
            self.logger.info(f"Module {module_name} installation initiated")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to install module {module_name}: {e}")
            return False
    
    def upgrade_module(self, module_name: str) -> bool:
        """
        Upgrade a module in Odoo.
        
        Args:
            module_name: Name of the module to upgrade
            
        Returns:
            True if upgrade successful, False otherwise
        """
        try:
            # Find the module
            module_ids = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'search',
                [[['name', '=', module_name]]]
            )
            
            if not module_ids:
                self.logger.error(f"Module {module_name} not found")
                return False
            
            # Upgrade the module
            self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'button_immediate_upgrade',
                [module_ids]
            )
            
            self.logger.info(f"Module {module_name} upgrade initiated")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upgrade module {module_name}: {e}")
            return False
    
    def uninstall_module(self, module_name: str) -> bool:
        """
        Uninstall a module from Odoo.
        
        Args:
            module_name: Name of the module to uninstall
            
        Returns:
            True if uninstallation successful, False otherwise
        """
        try:
            # Find the module
            module_ids = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'search',
                [[['name', '=', module_name]]]
            )
            
            if not module_ids:
                self.logger.error(f"Module {module_name} not found")
                return False
            
            # Uninstall the module
            self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'button_immediate_uninstall',
                [module_ids]
            )
            
            self.logger.info(f"Module {module_name} uninstallation initiated")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to uninstall module {module_name}: {e}")
            return False
    
    def deploy_module(self, module_path: str, addons_path: str) -> bool:
        """
        Deploy a module to Odoo addons directory.
        
        Args:
            module_path: Path to the module directory
            addons_path: Path to Odoo addons directory
            
        Returns:
            True if deployment successful, False otherwise
        """
        try:
            module_name = os.path.basename(module_path)
            target_path = os.path.join(addons_path, module_name)
            
            # Remove existing module if it exists
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            
            # Copy module to addons directory
            shutil.copytree(module_path, target_path)
            
            self.logger.info(f"Module {module_name} deployed to {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deploy module: {e}")
            return False
    
    def update_modules_list(self) -> bool:
        """
        Update the modules list in Odoo (equivalent to "Update Apps List").
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                'ir.module.module', 'update_list',
                []
            )
            
            self.logger.info("Modules list updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update modules list: {e}")
            return False
    
    def create_module_package(self, module_path: str, output_path: str) -> bool:
        """
        Create a ZIP package of the module for distribution.
        
        Args:
            module_path: Path to the module directory
            output_path: Path for the output ZIP file
            
        Returns:
            True if packaging successful, False otherwise
        """
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(module_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, os.path.dirname(module_path))
                        zipf.write(file_path, arc_name)
            
            self.logger.info(f"Module package created: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create module package: {e}")
            return False
    
    def deploy_and_install(self, module_path: str, addons_path: str) -> Tuple[bool, str]:
        """
        Deploy module and install it in one operation.
        
        Args:
            module_path: Path to the module directory
            addons_path: Path to Odoo addons directory
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        module_name = os.path.basename(module_path)
        
        # Deploy module
        if not self.deploy_module(module_path, addons_path):
            return False, f"Failed to deploy module {module_name}"
        
        # Update modules list
        if not self.update_modules_list():
            return False, f"Failed to update modules list after deploying {module_name}"
        
        # Install module
        if not self.install_module(module_name):
            return False, f"Failed to install module {module_name}"
        
        return True, f"Module {module_name} deployed and installed successfully"
    
    def get_database_list(self) -> List[str]:
        """
        Get list of available databases.
        
        Returns:
            List of database names
        """
        try:
            if not self._common:
                return []
            
            databases = self._common.list()
            return databases
            
        except Exception as e:
            self.logger.error(f"Failed to get database list: {e}")
            return []
    
    def execute_query(self, model: str, method: str, args: List = None, 
                     kwargs: Dict = None) -> Any:
        """
        Execute a generic query on Odoo.
        
        Args:
            model: Odoo model name
            method: Method to call
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Query result
        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        
        try:
            result = self._models.execute_kw(
                self.connection.database, self._uid, self.connection.password,
                model, method, args, kwargs
            )
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute query {model}.{method}: {e}")
            raise
    
    def validate_module_structure(self, module_path: str) -> List[str]:
        """
        Validate the structure of an Odoo module.
        
        Args:
            module_path: Path to the module directory
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check if directory exists
        if not os.path.exists(module_path):
            errors.append(f"Module directory does not exist: {module_path}")
            return errors
        
        # Check for required files
        manifest_file = os.path.join(module_path, "__manifest__.py")
        if not os.path.exists(manifest_file):
            errors.append("Missing __manifest__.py file")
        
        init_file = os.path.join(module_path, "__init__.py")
        if not os.path.exists(init_file):
            errors.append("Missing __init__.py file")
        
        # Validate manifest file
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_content = f.read()
                
                # Try to evaluate the manifest
                manifest_dict = eval(manifest_content)
                
                # Check required fields
                required_fields = ['name', 'version', 'depends']
                for field in required_fields:
                    if field not in manifest_dict:
                        errors.append(f"Missing required field in manifest: {field}")
                        
            except Exception as e:
                errors.append(f"Invalid manifest file: {e}")
        
        return errors