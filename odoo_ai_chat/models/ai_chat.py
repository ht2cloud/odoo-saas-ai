# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AIChatSession(models.Model):
    _name = 'ai.chat.session'
    _description = 'AI Chat Session'
    _order = 'create_date desc'
    
    name = fields.Char('Session Name', required=True)
    session_id = fields.Char('Session ID', required=True, index=True)
    requirements = fields.Text('Requirements', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('parsing', 'Parsing'),
        ('generating', 'Generating'),
        ('analyzing', 'Analyzing'),
        ('completing', 'Completing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending', string='Status')
    progress = fields.Integer('Progress', default=0)
    result_data = fields.Text('Result Data')
    error_message = fields.Text('Error Message')
    module_name = fields.Char('Generated Module Name')
    security_score = fields.Float('Security Score')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    
    @api.model
    def create_session(self, requirements, session_id=None):
        """Create a new chat session"""
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
        
        session = self.create({
            'name': requirements[:50] + '...' if len(requirements) > 50 else requirements,
            'session_id': session_id,
            'requirements': requirements,
        })
        return session
    
    def update_progress(self, progress, status=None):
        """Update session progress"""
        vals = {'progress': progress}
        if status:
            vals['status'] = status
        self.write(vals)
    
    def set_completed(self, result_data):
        """Mark session as completed with results"""
        self.write({
            'status': 'completed',
            'progress': 100,
            'result_data': result_data,
            'module_name': result_data.get('module_name'),
            'security_score': result_data.get('security_score', 0)
        })
    
    def set_failed(self, error_message):
        """Mark session as failed"""
        self.write({
            'status': 'failed',
            'progress': 0,
            'error_message': error_message
        })