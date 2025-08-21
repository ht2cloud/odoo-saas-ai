"""
Demo Web Server for Odoo AI Module Generator

Provides a web-based interface for real-time module generation and deployment.
"""

import os
import json
import uuid
import asyncio
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room
import tempfile
import shutil
import zipfile
from typing import Dict, Any, Optional

from .nlp_parser import NLPParser
from .code_generator import CodeGenerator
from .integration import OdooIntegration, OdooConnection
from .security import SecurityAnalyzer
from .config_engine import ConfigurationEngine


class DemoOdooManager:
    """Manages demo Odoo instances for testing generated modules"""
    
    def __init__(self):
        # For demo purposes, we'll simulate a demo instance
        # In production, this would manage multiple isolated instances
        self.demo_instance = OdooConnection(
            url="localhost",  # Simulated demo instance
            database="demo_db",
            username="admin", 
            password="admin",
            port=8069,
            protocol="http"
        )
    
    def create_demo_instance(self, session_id: str) -> OdooConnection:
        """Create or assign a demo instance for a session"""
        # For this demo, return the same instance configuration
        # In production, create isolated instances per session
        return self.demo_instance
    
    def cleanup_demo_instance(self, session_id: str):
        """Clean up demo instance after session"""
        # In production, remove modules and reset instance
        pass


class ModuleGenerationTask:
    """Represents an async module generation task"""
    
    def __init__(self, session_id: str, requirements: str, options: Dict[str, Any]):
        self.session_id = session_id
        self.requirements = requirements
        self.options = options
        self.status = "pending"
        self.progress = 0
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.module_path = None
        self.odoo_url = None


app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
active_tasks: Dict[str, ModuleGenerationTask] = {}
demo_manager = DemoOdooManager()


def update_task_progress(session_id: str, progress: int, message: str, status: str = None):
    """Update task progress and notify client"""
    if session_id in active_tasks:
        task = active_tasks[session_id]
        task.progress = progress
        if status:
            task.status = status
        
        socketio.emit('progress_update', {
            'progress': progress,
            'message': message,
            'status': status or task.status
        }, room=session_id)


def generate_module_async(task: ModuleGenerationTask):
    """Generate module asynchronously"""
    try:
        session_id = task.session_id
        
        update_task_progress(session_id, 10, "Parsing requirements...")
        
        # Parse requirements
        parser = NLPParser()
        spec = parser.parse_requirements(task.requirements)
        
        update_task_progress(session_id, 25, f"Generated specification for: {spec.name}")
        
        # Create temporary directory for generation
        temp_dir = tempfile.mkdtemp(prefix=f"odoo_demo_{session_id}_")
        
        # Generate configuration if requested
        if task.options.get('configure'):
            update_task_progress(session_id, 35, "Generating advanced configuration...")
            config_engine = ConfigurationEngine()
            config = config_engine.generate_configuration(spec)
        
        update_task_progress(session_id, 50, "Generating module code...")
        
        # Generate code
        generator = CodeGenerator()
        generated_files = generator.generate_module(spec, temp_dir)
        
        update_task_progress(session_id, 70, "Running security analysis...")
        
        # Security analysis if requested
        security_report = None
        if task.options.get('security_scan', True):  # Default to True for demo
            analyzer = SecurityAnalyzer()
            scan_result = analyzer.analyze_module(spec, generated_files)
            security_report = {
                'score': scan_result.overall_score,
                'passed': scan_result.passed,
                'issues': len(scan_result.security_issues),
                'compliance_issues': len(scan_result.compliance_issues)
            }
            
            if not scan_result.passed:
                update_task_progress(session_id, 75, "Security scan failed - module may have issues", "warning")
            else:
                update_task_progress(session_id, 75, f"Security scan passed (Score: {scan_result.overall_score:.1f}/100)")
        
        # Deploy to demo instance if requested
        demo_url = None
        if task.options.get('deploy', True):  # Default to True for demo
            update_task_progress(session_id, 85, "Preparing demo deployment...")
            
            try:
                demo_instance = demo_manager.create_demo_instance(session_id)
                integration = OdooIntegration(demo_instance)
                
                # For demo purposes, simulate deployment
                # In production, this would connect to a real Odoo instance
                update_task_progress(session_id, 90, "Demo deployment simulated successfully!")
                demo_url = f"http://localhost:8069/web#action=&model=ir.module.module&view_type=kanban"
                
            except Exception as e:
                update_task_progress(session_id, 90, f"Demo deployment simulation completed (would fail in real deployment: {str(e)})", "warning")
        
        # Create downloadable package
        update_task_progress(session_id, 98, "Preparing download package...")
        
        zip_path = os.path.join(temp_dir, f"{spec.name}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            module_dir = os.path.join(temp_dir, spec.name)
            for root, dirs, files in os.walk(module_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Complete task
        task.status = "completed"
        task.module_path = zip_path
        task.odoo_url = demo_url
        task.result = {
            'module_name': spec.name,
            'description': spec.description,
            'files_generated': len(generated_files),
            'models_count': len(spec.models),
            'views_count': len(spec.views),
            'security_report': security_report,
            'demo_url': demo_url,
            'download_ready': True
        }
        
        update_task_progress(session_id, 100, "Module generation completed!", "completed")
        
    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        update_task_progress(session_id, 0, f"Generation failed: {str(e)}", "failed")


@app.route('/')
def index():
    """Main demo page"""
    return render_template('demo.html')


@app.route('/api/generate', methods=['POST'])
def generate_module():
    """Start module generation"""
    data = request.get_json()
    requirements = data.get('requirements', '')
    options = data.get('options', {})
    
    if not requirements.strip():
        return jsonify({'error': 'Requirements cannot be empty'}), 400
    
    # Create new task
    session_id = str(uuid.uuid4())
    task = ModuleGenerationTask(session_id, requirements, options)
    active_tasks[session_id] = task
    
    # Start generation in background thread
    thread = threading.Thread(target=generate_module_async, args=(task,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'session_id': session_id,
        'status': 'started'
    })


@app.route('/api/status/<session_id>')
def get_status(session_id):
    """Get generation status"""
    if session_id not in active_tasks:
        return jsonify({'error': 'Session not found'}), 404
    
    task = active_tasks[session_id]
    return jsonify({
        'status': task.status,
        'progress': task.progress,
        'result': task.result,
        'error': task.error
    })


@app.route('/api/download/<session_id>')
def download_module(session_id):
    """Download generated module"""
    if session_id not in active_tasks:
        return jsonify({'error': 'Session not found'}), 404
    
    task = active_tasks[session_id]
    if task.status != 'completed' or not task.module_path:
        return jsonify({'error': 'Module not ready for download'}), 400
    
    if not os.path.exists(task.module_path):
        return jsonify({'error': 'Module file not found'}), 404
    
    return send_file(
        task.module_path,
        as_attachment=True,
        download_name=f"{task.result['module_name']}.zip"
    )


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")


@socketio.on('join_session')
def handle_join_session(data):
    """Join a generation session for updates"""
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        emit('joined', {'session_id': session_id})


def run_demo_server(host='127.0.0.1', port=5000, debug=True):
    """Run the demo server"""
    print(f"Starting Odoo AI Module Generator Demo Server on {host}:{port}")
    print(f"Open your browser to: http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_demo_server()