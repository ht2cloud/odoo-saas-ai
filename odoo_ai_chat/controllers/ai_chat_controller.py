# -*- coding: utf-8 -*-

import json
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime

from odoo import http, api, registry, SUPERUSER_ID
from odoo.http import request

# Import the AI module generator components
import sys
import importlib.util

# Add the ai_module_generator to the path
ai_module_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ai_module_generator')
sys.path.insert(0, ai_module_path)

try:
    from ai_module_generator.nlp_parser import NLPParser
    from ai_module_generator.code_generator import CodeGenerator
    from ai_module_generator.integration import OdooIntegration, OdooConnection
    from ai_module_generator.security import SecurityAnalyzer
    from ai_module_generator.config_engine import ConfigurationEngine
except ImportError as e:
    logging.warning(f"Could not import AI module generator components: {e}")
    # Provide fallback implementations for development
    class NLPParser:
        def parse_requirements(self, requirements):
            return type('MockSpec', (), {
                'name': 'demo_module',
                'description': requirements,
                'models': [],
                'views': []
            })()
    
    class CodeGenerator:
        def generate_module(self, spec, output_dir):
            return {}
    
    class SecurityAnalyzer:
        def analyze_module(self, spec, files):
            return type('MockResult', (), {
                'overall_score': 85,
                'passed': True,
                'security_issues': [],
                'compliance_issues': []
            })()

_logger = logging.getLogger(__name__)

# Store active generation tasks
active_tasks = {}


class ModuleGenerationTask:
    """Represents an async module generation task"""
    
    def __init__(self, session_id: str, requirements: str, options: dict):
        self.session_id = session_id
        self.requirements = requirements
        self.options = options
        self.status = "pending"
        self.progress = 0
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.module_path = None


class AIChatController(http.Controller):
    
    @http.route('/ai_chat', type='http', auth='user', website=True)
    def ai_chat_index(self, **kwargs):
        """Main AI chat interface"""
        return request.render('odoo_ai_chat.ai_chat_main')
    
    @http.route('/ai_chat/generate', type='json', auth='user', methods=['POST'])
    def generate_module(self, requirements, options=None):
        """Start module generation process"""
        if not requirements or not requirements.strip():
            return {'error': 'Requirements cannot be empty'}
        
        session_id = str(uuid.uuid4())
        options = options or {}
        
        # Create generation task
        task = ModuleGenerationTask(session_id, requirements.strip(), options)
        active_tasks[session_id] = task
        
        # Start generation in background thread
        thread = threading.Thread(target=self._generate_module_async, args=(task,))
        thread.daemon = True
        thread.start()
        
        return {
            'session_id': session_id,
            'status': 'started',
            'message': 'Module generation started'
        }
    
    @http.route('/ai_chat/status/<session_id>', type='json', auth='user')
    def get_generation_status(self, session_id):
        """Get status of module generation"""
        if session_id not in active_tasks:
            return {'error': 'Session not found'}
        
        task = active_tasks[session_id]
        return {
            'status': task.status,
            'progress': task.progress,
            'result': task.result,
            'error': task.error
        }
    
    @http.route('/ai_chat/install/<session_id>', type='json', auth='user')
    def install_generated_module(self, session_id):
        """Install the generated module in current Odoo instance"""
        if session_id not in active_tasks:
            return {'error': 'Session not found'}
        
        task = active_tasks[session_id]
        if task.status != 'completed' or not task.result:
            return {'error': 'Module not ready for installation'}
        
        try:
            # Get current Odoo connection info
            db_name = request.env.cr.dbname
            
            # Create connection to current instance
            connection = OdooConnection(
                url='localhost',
                database=db_name,
                username='admin',  # This would need to be configurable
                password='admin',  # This would need to be configurable
                port=8069,
                protocol='http'
            )
            
            integration = OdooIntegration(connection)
            
            if integration.connect():
                # Deploy and install the module
                module_name = task.result.get('module_name')
                if module_name and task.module_path:
                    success, message = integration.deploy_and_install(
                        task.module_path,
                        "/opt/odoo/addons"  # This would need to be configurable
                    )
                    return {
                        'success': success,
                        'message': message,
                        'module_name': module_name
                    }
                else:
                    return {'error': 'Module information not available'}
            else:
                return {'error': 'Could not connect to Odoo instance'}
                
        except Exception as e:
            _logger.error(f"Error installing module: {e}")
            return {'error': f'Installation failed: {str(e)}'}
    
    def _generate_module_async(self, task):
        """Generate module asynchronously"""
        try:
            session_id = task.session_id
            
            # Update progress: Parsing requirements
            task.progress = 10
            task.status = "parsing"
            
            # Parse requirements
            parser = NLPParser()
            spec = parser.parse_requirements(task.requirements)
            
            # Update progress: Generating code
            task.progress = 30
            task.status = "generating"
            
            # Generate module code
            generator = CodeGenerator()
            
            # Create temporary directory for generation
            temp_dir = tempfile.mkdtemp()
            generated_files = generator.generate_module(spec, temp_dir)
            
            # Update progress: Security analysis
            task.progress = 60
            task.status = "analyzing"
            
            # Perform security analysis
            analyzer = SecurityAnalyzer()
            scan_result = analyzer.analyze_module(spec, generated_files)
            
            # Update progress: Completing
            task.progress = 90
            task.status = "completing"
            
            # Store module path for installation
            task.module_path = os.path.join(temp_dir, spec.name)
            
            # Prepare result
            task.result = {
                'module_name': spec.name,
                'description': spec.description,
                'files_generated': len(generated_files),
                'models_count': len(spec.models),
                'views_count': len(spec.views),
                'security_score': scan_result.overall_score,
                'security_passed': scan_result.passed,
                'security_issues': len(scan_result.security_issues),
                'compliance_issues': len(scan_result.compliance_issues),
                'temp_path': temp_dir
            }
            
            # Mark as completed
            task.progress = 100
            task.status = "completed"
            
        except Exception as e:
            _logger.error(f"Error generating module: {e}")
            task.error = str(e)
            task.status = "failed"
            task.progress = 0