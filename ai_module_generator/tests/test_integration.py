"""
Tests for Integration module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from ai_module_generator.integration import OdooIntegration, OdooConnection


class TestOdooIntegration(unittest.TestCase):
    
    def setUp(self):
        self.connection = OdooConnection(
            url="localhost",
            database="test_db",
            username="admin",
            password="admin",
            port=8069
        )
        self.integration = OdooIntegration(self.connection)
    
    def test_connection_config(self):
        """Test connection configuration"""
        self.assertEqual(self.connection.url, "localhost")
        self.assertEqual(self.connection.database, "test_db")
        self.assertEqual(self.connection.username, "admin")
        self.assertEqual(self.connection.full_url, "http://localhost:8069")
    
    @patch('ai_module_generator.integration.xmlrpc.client.ServerProxy')
    def test_successful_connection(self, mock_server_proxy):
        """Test successful connection to Odoo"""
        # Mock the common service
        mock_common = Mock()
        mock_common.authenticate.return_value = 1  # Valid user ID
        
        # Mock the models service
        mock_models = Mock()
        
        mock_server_proxy.side_effect = [mock_common, mock_models]
        
        result = self.integration.connect()
        
        self.assertTrue(result)
        self.assertEqual(self.integration._uid, 1)
        self.assertIsNotNone(self.integration._common)
        self.assertIsNotNone(self.integration._models)
    
    @patch('ai_module_generator.integration.xmlrpc.client.ServerProxy')
    def test_failed_authentication(self, mock_server_proxy):
        """Test failed authentication"""
        mock_common = Mock()
        mock_common.authenticate.return_value = False  # Authentication failed
        
        mock_server_proxy.return_value = mock_common
        
        result = self.integration.connect()
        
        self.assertFalse(result)
        self.assertIsNone(self.integration._uid)
    
    def test_module_exists_mock(self):
        """Test module existence check with mock"""
        # Mock the models service
        self.integration._models = Mock()
        self.integration._uid = 1
        self.integration._models.execute_kw.return_value = [1]  # Module found
        
        result = self.integration.module_exists("base")
        
        self.assertTrue(result)
        self.integration._models.execute_kw.assert_called_once()
    
    def test_get_installed_modules_mock(self):
        """Test getting installed modules with mock"""
        self.integration._models = Mock()
        self.integration._uid = 1
        
        mock_modules = [
            {"name": "base", "display_name": "Base", "version": "15.0.1.0.0"},
            {"name": "sale", "display_name": "Sales", "version": "15.0.1.0.0"}
        ]
        self.integration._models.execute_kw.return_value = mock_modules
        
        result = self.integration.get_installed_modules()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "base")
        self.assertEqual(result[1]["name"], "sale")
    
    def test_get_module_info_mock(self):
        """Test getting module info with mock"""
        self.integration._models = Mock()
        self.integration._uid = 1
        
        mock_module_info = [{
            "name": "test_module",
            "display_name": "Test Module",
            "version": "1.0.0",
            "state": "installed"
        }]
        self.integration._models.execute_kw.return_value = mock_module_info
        
        result = self.integration.get_module_info("test_module")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "test_module")
        self.assertEqual(result["state"], "installed")
    
    def test_get_module_info_not_found(self):
        """Test getting info for non-existent module"""
        self.integration._models = Mock()
        self.integration._uid = 1
        self.integration._models.execute_kw.return_value = []  # No module found
        
        result = self.integration.get_module_info("non_existent_module")
        
        self.assertIsNone(result)
    
    @patch('ai_module_generator.integration.shutil.copytree')
    @patch('ai_module_generator.integration.shutil.rmtree')
    @patch('ai_module_generator.integration.os.path.exists')
    @patch('ai_module_generator.integration.os.path.basename')
    def test_deploy_module(self, mock_basename, mock_exists, mock_rmtree, mock_copytree):
        """Test module deployment"""
        mock_basename.return_value = "test_module"
        mock_exists.return_value = False  # Target doesn't exist
        
        result = self.integration.deploy_module("/path/to/test_module", "/opt/odoo/addons")
        
        self.assertTrue(result)
        mock_copytree.assert_called_once_with(
            "/path/to/test_module", 
            "/opt/odoo/addons/test_module"
        )
    
    @patch('ai_module_generator.integration.zipfile.ZipFile')
    @patch('ai_module_generator.integration.os.walk')
    def test_create_module_package(self, mock_walk, mock_zipfile):
        """Test module packaging"""
        mock_walk.return_value = [
            ("/path/to/module", ["models"], ["__manifest__.py", "__init__.py"]),
            ("/path/to/module/models", [], ["customer.py", "__init__.py"])
        ]
        
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        result = self.integration.create_module_package(
            "/path/to/module", 
            "/output/module.zip"
        )
        
        self.assertTrue(result)
        # Should have called write for each file
        self.assertTrue(mock_zip.write.called)
    
    def test_validate_module_structure_missing_directory(self):
        """Test module structure validation with missing directory"""
        errors = self.integration.validate_module_structure("/non/existent/path")
        
        self.assertTrue(len(errors) > 0)
        self.assertIn("does not exist", errors[0])
    
    @patch('ai_module_generator.integration.os.path.exists')
    def test_validate_module_structure_missing_manifest(self, mock_exists):
        """Test module structure validation with missing manifest"""
        def exists_side_effect(path):
            if path.endswith("__manifest__.py"):
                return False
            return True
        
        mock_exists.side_effect = exists_side_effect
        
        errors = self.integration.validate_module_structure("/valid/path")
        
        self.assertTrue(any("Missing __manifest__.py" in error for error in errors))
    
    @patch('ai_module_generator.integration.os.path.exists')
    @patch('builtins.open', create=True)
    def test_validate_module_structure_valid(self, mock_open, mock_exists):
        """Test module structure validation with valid module"""
        mock_exists.return_value = True
        
        # Mock manifest file content
        manifest_content = """
{
    'name': 'Test Module',
    'version': '1.0.0',
    'depends': ['base'],
}
"""
        mock_open.return_value.__enter__.return_value.read.return_value = manifest_content
        
        errors = self.integration.validate_module_structure("/valid/path")
        
        self.assertEqual(len(errors), 0)
    
    def test_execute_query_mock(self):
        """Test generic query execution"""
        self.integration._models = Mock()
        self.integration._uid = 1
        self.integration.connection = self.connection
        
        expected_result = [{"id": 1, "name": "Test Record"}]
        self.integration._models.execute_kw.return_value = expected_result
        
        result = self.integration.execute_query(
            "test.model", 
            "search_read", 
            [[]], 
            {"fields": ["name"]}
        )
        
        self.assertEqual(result, expected_result)
        self.integration._models.execute_kw.assert_called_once_with(
            "test_db", 1, "admin",
            "test.model", "search_read",
            [[]],
            {"fields": ["name"]}
        )


if __name__ == '__main__':
    unittest.main()