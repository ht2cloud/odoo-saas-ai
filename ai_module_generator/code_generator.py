"""
Automated Code Generator

Translates structured specifications into Odoo-compliant Python and XML files.
Generates models, views, menus, actions, and reports.
"""

import os
import json
from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, Template
from datetime import datetime

from .nlp_parser import ModuleSpec, Model, Field, View, MenuAction, FieldType


class CodeGenerator:
    """
    Generates Odoo module code from structured specifications.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the code generator.
        
        Args:
            template_dir: Directory containing Jinja2 templates
        """
        if template_dir and os.path.exists(template_dir):
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            # Use built-in templates
            self.env = Environment(loader=FileSystemLoader(self._get_builtin_template_dir()))
        
        # Configure Jinja2 environment
        self.env.globals['now'] = datetime.now
        self.env.globals['field_type_mapping'] = self._get_field_type_mapping()
    
    def generate_module(self, spec: ModuleSpec, output_dir: str) -> Dict[str, str]:
        """
        Generate complete Odoo module from specification.
        
        Args:
            spec: Module specification
            output_dir: Directory to write generated files
            
        Returns:
            Dict mapping file paths to generated content
        """
        module_dir = os.path.join(output_dir, spec.name)
        os.makedirs(module_dir, exist_ok=True)
        
        generated_files = {}
        
        # Generate manifest file
        manifest_content = self._generate_manifest(spec)
        manifest_path = os.path.join(module_dir, "__manifest__.py")
        generated_files[manifest_path] = manifest_content
        
        # Generate __init__.py
        init_content = self._generate_init_file(spec)
        init_path = os.path.join(module_dir, "__init__.py")
        generated_files[init_path] = init_content
        
        # Generate models
        if spec.models:
            models_dir = os.path.join(module_dir, "models")
            os.makedirs(models_dir, exist_ok=True)
            
            models_init_content = self._generate_models_init(spec.models)
            models_init_path = os.path.join(models_dir, "__init__.py")
            generated_files[models_init_path] = models_init_content
            
            for model in spec.models:
                model_content = self._generate_model_file(model)
                model_filename = f"{model.name.split('.')[-1]}.py"
                model_path = os.path.join(models_dir, model_filename)
                generated_files[model_path] = model_content
        
        # Generate views
        if spec.views:
            views_dir = os.path.join(module_dir, "views")
            os.makedirs(views_dir, exist_ok=True)
            
            views_content = self._generate_views_file(spec.views)
            views_path = os.path.join(views_dir, f"{spec.name}_views.xml")
            generated_files[views_path] = views_content
        
        # Generate menu and actions
        if spec.menu_actions:
            menu_content = self._generate_menu_file(spec)
            menu_path = os.path.join(module_dir, "views", f"{spec.name}_menu.xml")
            generated_files[menu_path] = menu_content
        
        # Generate security file
        security_content = self._generate_security_file(spec)
        security_dir = os.path.join(module_dir, "security")
        os.makedirs(security_dir, exist_ok=True)
        security_path = os.path.join(security_dir, "ir.model.access.csv")
        generated_files[security_path] = security_content
        
        # Write all files
        for file_path, content in generated_files.items():
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return generated_files
    
    def _get_builtin_template_dir(self) -> str:
        """Get the directory containing built-in templates"""
        # For now, we'll generate templates programmatically
        # In a real implementation, these would be separate template files
        return os.path.dirname(__file__)
    
    def _get_field_type_mapping(self) -> Dict[FieldType, str]:
        """Get mapping from our field types to Odoo field types"""
        return {
            FieldType.CHAR: "fields.Char",
            FieldType.TEXT: "fields.Text", 
            FieldType.INTEGER: "fields.Integer",
            FieldType.FLOAT: "fields.Float",
            FieldType.BOOLEAN: "fields.Boolean",
            FieldType.DATE: "fields.Date",
            FieldType.DATETIME: "fields.Datetime",
            FieldType.SELECTION: "fields.Selection",
            FieldType.MANY2ONE: "fields.Many2one",
            FieldType.ONE2MANY: "fields.One2many",
            FieldType.MANY2MANY: "fields.Many2many",
            FieldType.BINARY: "fields.Binary",
            FieldType.HTML: "fields.Html",
            FieldType.MONETARY: "fields.Monetary",
        }
    
    def _generate_manifest(self, spec: ModuleSpec) -> str:
        """Generate __manifest__.py file"""
        data_files = []
        
        if spec.views:
            data_files.append(f"'views/{spec.name}_views.xml'")
        
        if spec.menu_actions:
            data_files.append(f"'views/{spec.name}_menu.xml'")
        
        data_files.append("'security/ir.model.access.csv'")
        
        return f"""# -*- coding: utf-8 -*-
{{
    'name': '{spec.display_name}',
    'version': '{spec.version}',
    'category': '{spec.category}',
    'summary': 'AI-generated Odoo module',
    'description': '''
{spec.description}
    ''',
    'author': '{spec.author}',
    'depends': {spec.depends},
    'data': [
        {','.join(['        ' + f for f in data_files])}
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}}
"""
    
    def _generate_init_file(self, spec: ModuleSpec) -> str:
        """Generate module __init__.py file"""
        imports = []
        if spec.models:
            imports.append("from . import models")
        
        if not imports:
            return "# -*- coding: utf-8 -*-\n"
        
        return f"""# -*- coding: utf-8 -*-

{chr(10).join(imports)}
"""
    
    def _generate_models_init(self, models: List[Model]) -> str:
        """Generate models __init__.py file"""
        imports = []
        for model in models:
            model_name = model.name.split('.')[-1]
            imports.append(f"from . import {model_name}")
        
        return f"""# -*- coding: utf-8 -*-

{chr(10).join(imports)}
"""
    
    def _generate_model_file(self, model: Model) -> str:
        """Generate individual model Python file"""
        field_type_mapping = self._get_field_type_mapping()
        
        fields_code = []
        for field in model.fields:
            field_def = self._generate_field_definition(field, field_type_mapping)
            fields_code.append(f"    {field_def}")
        
        inherit_str = ""
        if model.inherit:
            inherit_str = f"    _inherit = '{model.inherit}'"
        
        rec_name_str = ""
        if model.rec_name and model.rec_name != "name":
            rec_name_str = f"    _rec_name = '{model.rec_name}'"
        
        order_str = ""
        if model.order:
            order_str = f"    _order = '{model.order}'"
        
        return f"""# -*- coding: utf-8 -*-

from odoo import models, fields, api


class {self._to_class_name(model.name)}(models.Model):
    _name = '{model.name}'
    _description = '{model.description}'
{inherit_str}
{rec_name_str}
{order_str}

{chr(10).join(fields_code)}
"""
    
    def _generate_field_definition(self, field: Field, field_type_mapping: Dict[FieldType, str]) -> str:
        """Generate field definition code"""
        field_type = field_type_mapping[field.field_type]
        params = []
        
        if field.string:
            params.append(f"string='{field.string}'")
        
        if field.required:
            params.append("required=True")
        
        if field.readonly:
            params.append("readonly=True")
        
        if field.help:
            params.append(f"help='{field.help}'")
        
        if field.default is not None:
            if isinstance(field.default, str):
                params.append(f"default='{field.default}'")
            else:
                params.append(f"default={field.default}")
        
        if field.domain:
            params.append(f"domain={field.domain}")
        
        if field.relation:
            params.append(f"comodel_name='{field.relation}'")
        
        if field.selection_options:
            selection_str = str(field.selection_options)
            params.append(f"selection={selection_str}")
        
        params_str = ", ".join(params) if params else ""
        return f"{field.name} = {field_type}({params_str})"
    
    def _generate_views_file(self, views: List[View]) -> str:
        """Generate views XML file"""
        xml_content = ['<?xml version="1.0" encoding="utf-8"?>', '<odoo>', '    <data>']
        
        for view in views:
            view_xml = f"""
        <record id="{view.name}" model="ir.ui.view">
            <field name="name">{view.name}</field>
            <field name="model">{view.model}</field>
            <field name="arch" type="xml">
                {view.arch}
            </field>
        </record>"""
            xml_content.append(view_xml)
        
        xml_content.extend(['    </data>', '</odoo>'])
        return '\n'.join(xml_content)
    
    def _generate_menu_file(self, spec: ModuleSpec) -> str:
        """Generate menu and actions XML file"""
        xml_content = ['<?xml version="1.0" encoding="utf-8"?>', '<odoo>', '    <data>']
        
        # Generate actions
        for action in spec.menu_actions:
            action_id = f"action_{action.model.replace('.', '_')}"
            action_xml = f"""
        <record id="{action_id}" model="ir.actions.act_window">
            <field name="name">{action.name}</field>
            <field name="res_model">{action.model}</field>
            <field name="view_mode">{action.view_mode}</field>"""
            
            if action.domain:
                action_xml += f'\n            <field name="domain">{action.domain}</field>'
            
            if action.context:
                action_xml += f'\n            <field name="context">{action.context}</field>'
            
            action_xml += '\n        </record>'
            xml_content.append(action_xml)
        
        # Generate main menu
        main_menu_id = f"menu_{spec.name}"
        main_menu_xml = f"""
        <menuitem id="{main_menu_id}"
                  name="{spec.display_name}"
                  sequence="10"/>"""
        xml_content.append(main_menu_xml)
        
        # Generate submenus
        for i, action in enumerate(spec.menu_actions):
            action_id = f"action_{action.model.replace('.', '_')}"
            submenu_id = f"menu_{action.model.replace('.', '_')}"
            submenu_xml = f"""
        <menuitem id="{submenu_id}"
                  name="{action.name}"
                  parent="{main_menu_id}"
                  action="{action_id}"
                  sequence="{(i + 1) * 10}"/>"""
            xml_content.append(submenu_xml)
        
        xml_content.extend(['    </data>', '</odoo>'])
        return '\n'.join(xml_content)
    
    def _generate_security_file(self, spec: ModuleSpec) -> str:
        """Generate security/access rights CSV file"""
        if not spec.models:
            return "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
        
        lines = ["id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"]
        
        for model in spec.models:
            model_name = model.name.replace('.', '_')
            access_id = f"access_{model_name}"
            model_id = f"model_{model_name}"
            line = f"{access_id},Access {model.description},{model_id},base.group_user,1,1,1,1"
            lines.append(line)
        
        return '\n'.join(lines) + '\n'
    
    def _to_class_name(self, model_name: str) -> str:
        """Convert model name to Python class name"""
        parts = model_name.split('.')
        return ''.join(word.capitalize() for word in parts)
    
    def validate_generated_code(self, file_path: str) -> List[str]:
        """
        Validate generated Python code for syntax errors.
        
        Args:
            file_path: Path to the Python file to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Try to compile the code
            compile(code, file_path, 'exec')
            
        except SyntaxError as e:
            errors.append(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            errors.append(f"Error validating {file_path}: {e}")
        
        return errors
    
    def generate_test_cases(self, spec: ModuleSpec) -> str:
        """
        Generate basic test cases for the module.
        
        Args:
            spec: Module specification
            
        Returns:
            Test case code
        """
        if not spec.models:
            return ""
        
        test_code = f"""# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class Test{self._to_class_name(spec.name)}(TransactionCase):
    
    def setUp(self):
        super().setUp()
        # Set up test data here
    
"""
        
        for model in spec.models:
            class_name = self._to_class_name(model.name)
            test_method = f"""    def test_create_{model.name.split('.')[-1]}(self):
        \"\"\"Test creating a {model.description}\"\"\"
        record = self.env['{model.name}'].create({{
            'name': 'Test {model.description}',
        }})
        self.assertTrue(record)
        self.assertEqual(record.name, 'Test {model.description}')
    
"""
            test_code += test_method
        
        return test_code