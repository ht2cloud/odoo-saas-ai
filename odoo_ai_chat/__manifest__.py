# -*- coding: utf-8 -*-
{
    'name': 'AI Module Generator Chat',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': 'AI-powered module generation with chat interface',
    'description': """
        AI Module Generator Chat
        ========================
        
        This module provides an AI-powered chat interface for generating Odoo modules
        from natural language requirements. Users can describe their needs in plain
        English and get complete, working Odoo modules instantly.
        
        Features:
        - Natural language processing for module requirements
        - Real-time module generation with progress updates
        - Security analysis and compliance checking  
        - Direct module installation within Odoo
        - Interactive chat interface
    """,
    'author': 'HT2Cloud',
    'website': 'https://github.com/ht2cloud/odoo-saas-ai',
    'license': 'MIT',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_chat_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_ai_chat/static/src/js/ai_chat_widget.js',
            'odoo_ai_chat/static/src/css/ai_chat.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}