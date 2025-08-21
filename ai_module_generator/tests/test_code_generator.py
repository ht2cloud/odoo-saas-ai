"""
Tests for Code Generator module
"""

import unittest
import tempfile
import os
import shutil
from ai_module_generator.nlp_parser import NLPParser, ModuleSpec, Model, Field, FieldType
from ai_module_generator.code_generator import CodeGenerator


class TestCodeGenerator(unittest.TestCase):
    
    def setUp(self):
        self.generator = CodeGenerator()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a simple test specification
        self.test_spec = ModuleSpec(
            name="test_module",
            display_name="Test Module",
            description="A test module for unit testing",
            models=[
                Model(
                    name="test.customer",
                    description="Customer Management",
                    table_name="test_customer",
                    fields=[
                        Field(name="name", field_type=FieldType.CHAR, string="Name", required=True),
                        Field(name="email", field_type=FieldType.CHAR, string="Email"),
                        Field(name="active", field_type=FieldType.BOOLEAN, string="Active", default=True)
                    ]
                )
            ]
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_generate_manifest(self):
        """Test manifest file generation"""
        manifest_content = self.generator._generate_manifest(self.test_spec)
        
        self.assertIn("'name': 'Test Module'", manifest_content)
        self.assertIn("'version': '1.0.0'", manifest_content)
        self.assertIn("'depends': ['base']", manifest_content)
        self.assertIn("'installable': True", manifest_content)
    
    def test_generate_model_file(self):
        """Test model file generation"""
        model = self.test_spec.models[0]
        model_content = self.generator._generate_model_file(model)
        
        self.assertIn("class TestCustomer(models.Model):", model_content)
        self.assertIn("_name = 'test.customer'", model_content)
        self.assertIn("_description = 'Customer Management'", model_content)
        self.assertIn("name = fields.Char(string='Name', required=True)", model_content)
        self.assertIn("email = fields.Char(string='Email')", model_content)
        self.assertIn("active = fields.Boolean(string='Active', default=True)", model_content)
    
    def test_generate_complete_module(self):
        """Test complete module generation"""
        generated_files = self.generator.generate_module(self.test_spec, self.temp_dir)
        
        # Check that all expected files were generated
        expected_files = [
            "__manifest__.py",
            "__init__.py",
            "models/__init__.py",
            "models/customer.py",
            "security/ir.model.access.csv"
        ]
        
        for expected_file in expected_files:
            full_path = os.path.join(self.temp_dir, "test_module", expected_file)
            self.assertTrue(os.path.exists(full_path), f"Missing file: {expected_file}")
            self.assertIn(full_path, generated_files)
    
    def test_generate_views_file(self):
        """Test views XML generation"""
        # Add views to test spec
        from ai_module_generator.nlp_parser import View
        
        test_views = [
            View(
                name="test_customer_form_view",
                model="test.customer",
                view_type="form",
                arch="<form><sheet><group><field name='name'/></group></sheet></form>"
            ),
            View(
                name="test_customer_tree_view", 
                model="test.customer",
                view_type="tree",
                arch="<tree><field name='name'/></tree>"
            )
        ]
        
        views_content = self.generator._generate_views_file(test_views)
        
        self.assertIn('<?xml version="1.0" encoding="utf-8"?>', views_content)
        self.assertIn('<odoo>', views_content)
        self.assertIn('record id="test_customer_form_view"', views_content)
        self.assertIn('model="ir.ui.view"', views_content)
        self.assertIn('<field name="name">test_customer_form_view</field>', views_content)
    
    def test_generate_menu_file(self):
        """Test menu XML generation"""
        # Add menu actions to test spec
        from ai_module_generator.nlp_parser import MenuAction
        
        self.test_spec.menu_actions = [
            MenuAction(
                name="Customers",
                model="test.customer",
                view_mode="tree,form"
            )
        ]
        
        menu_content = self.generator._generate_menu_file(self.test_spec)
        
        self.assertIn('record id="action_test_customer"', menu_content)
        self.assertIn('model="ir.actions.act_window"', menu_content)
        self.assertIn('<field name="res_model">test.customer</field>', menu_content)
        self.assertIn('<field name="view_mode">tree,form</field>', menu_content)
        self.assertIn('menuitem id="menu_test_module"', menu_content)
    
    def test_generate_security_file(self):
        """Test security CSV generation"""
        security_content = self.generator._generate_security_file(self.test_spec)
        
        lines = security_content.strip().split('\n')
        self.assertTrue(len(lines) >= 2)  # Header + at least one access rule
        
        # Check header
        header = lines[0]
        self.assertIn("id,name,model_id:id,group_id:id", header)
        
        # Check access rule
        if len(lines) > 1:
            access_rule = lines[1]
            self.assertIn("access_test_customer", access_rule)
            self.assertIn("model_test_customer", access_rule)
    
    def test_field_definition_generation(self):
        """Test individual field definition generation"""
        field_type_mapping = self.generator._get_field_type_mapping()
        
        # Test various field types
        test_fields = [
            Field(name="name", field_type=FieldType.CHAR, string="Name", required=True),
            Field(name="amount", field_type=FieldType.FLOAT, string="Amount"),
            Field(name="partner_id", field_type=FieldType.MANY2ONE, string="Partner", relation="res.partner"),
            Field(name="state", field_type=FieldType.SELECTION, string="State", 
                 selection_options=[('draft', 'Draft'), ('done', 'Done')])
        ]
        
        for field in test_fields:
            field_def = self.generator._generate_field_definition(field, field_type_mapping)
            
            self.assertIn(f"{field.name} = ", field_def)
            self.assertIn(f"string='{field.string}'", field_def)
            
            if field.required:
                self.assertIn("required=True", field_def)
            
            if field.relation:
                self.assertIn(f"comodel_name='{field.relation}'", field_def)
            
            if field.selection_options:
                self.assertIn("selection=", field_def)
    
    def test_class_name_conversion(self):
        """Test model name to class name conversion"""
        test_cases = [
            ("test.customer", "TestCustomer"),
            ("custom.sales.order", "CustomSalesOrder"),
            ("hr.employee", "HrEmployee")
        ]
        
        for model_name, expected_class in test_cases:
            actual_class = self.generator._to_class_name(model_name)
            self.assertEqual(actual_class, expected_class)
    
    def test_validate_generated_code(self):
        """Test Python code validation"""
        # Generate a module and validate the Python files
        generated_files = self.generator.generate_module(self.test_spec, self.temp_dir)
        
        python_files = [path for path in generated_files.keys() if path.endswith('.py')]
        
        for python_file in python_files:
            errors = self.generator.validate_generated_code(python_file)
            self.assertEqual(len(errors), 0, f"Validation errors in {python_file}: {errors}")
    
    def test_generate_test_cases(self):
        """Test test case generation"""
        test_code = self.generator.generate_test_cases(self.test_spec)
        
        self.assertIn("class TestTestModule(TransactionCase):", test_code)
        self.assertIn("def test_create_customer(self):", test_code)
        self.assertIn("self.env['test.customer'].create(", test_code)
        self.assertIn("self.assertEqual(record.name", test_code)
    
    def test_multiple_models(self):
        """Test generation with multiple models"""
        # Add another model to test spec
        order_model = Model(
            name="test.order",
            description="Order Management", 
            table_name="test_order",
            fields=[
                Field(name="name", field_type=FieldType.CHAR, string="Order Number", required=True),
                Field(name="customer_id", field_type=FieldType.MANY2ONE, string="Customer", relation="test.customer"),
                Field(name="total", field_type=FieldType.FLOAT, string="Total Amount")
            ]
        )
        
        self.test_spec.models.append(order_model)
        
        generated_files = self.generator.generate_module(self.test_spec, self.temp_dir)
        
        # Should generate files for both models
        customer_model_file = os.path.join(self.temp_dir, "test_module", "models", "customer.py")
        order_model_file = os.path.join(self.temp_dir, "test_module", "models", "order.py")
        
        self.assertTrue(os.path.exists(customer_model_file))
        self.assertTrue(os.path.exists(order_model_file))
        
        # Check models init file includes both
        models_init_file = os.path.join(self.temp_dir, "test_module", "models", "__init__.py")
        with open(models_init_file, 'r') as f:
            init_content = f.read()
        
        self.assertIn("from . import customer", init_content)
        self.assertIn("from . import order", init_content)


if __name__ == '__main__':
    unittest.main()