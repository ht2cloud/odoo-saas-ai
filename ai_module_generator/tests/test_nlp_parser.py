"""
Tests for NLP Parser module
"""

import unittest
from ai_module_generator.nlp_parser import (
    NLPParser, ModuleSpec, Model, Field, FieldType, View, MenuAction
)


class TestNLPParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = NLPParser()
    
    def test_simple_sales_dashboard(self):
        """Test parsing of simple sales dashboard requirement"""
        requirement = "I need a sales dashboard that tracks monthly revenue and customer leads."
        
        spec = self.parser.parse_requirements(requirement)
        
        self.assertIsInstance(spec, ModuleSpec)
        self.assertTrue(spec.name.startswith("custom_"))
        self.assertIn("sales", spec.name.lower())
        self.assertTrue(len(spec.models) > 0)
        
        # Check for expected entities
        model_names = [model.name for model in spec.models]
        self.assertTrue(any("sales" in name or "revenue" in name or "lead" in name 
                          for name in model_names))
    
    def test_extract_business_entities(self):
        """Test business entity extraction"""
        text = "I need to manage customers, products, and sales orders"
        entities = self.parser._extract_business_entities(text)
        
        expected_entities = ['customer', 'product', 'sales']
        for entity in expected_entities:
            self.assertIn(entity, entities)
    
    def test_field_generation(self):
        """Test field generation for entities"""
        requirement = "I need to track customer information with name, email, phone, and address"
        
        spec = self.parser.parse_requirements(requirement)
        
        # Find customer model
        customer_model = None
        for model in spec.models:
            if "customer" in model.name:
                customer_model = model
                break
        
        self.assertIsNotNone(customer_model)
        
        # Check for expected fields
        field_names = [field.name for field in customer_model.fields]
        expected_fields = ['name', 'email', 'phone', 'address']
        for expected_field in expected_fields:
            self.assertTrue(any(expected_field in fname for fname in field_names))
    
    def test_view_generation(self):
        """Test view generation"""
        requirement = "Create a dashboard for project management"
        
        spec = self.parser.parse_requirements(requirement)
        
        self.assertTrue(len(spec.views) > 0)
        
        # Should have at least form and tree views
        view_types = [view.view_type for view in spec.views]
        self.assertIn('form', view_types)
        self.assertIn('tree', view_types)
        
        # Dashboard requirement should add kanban view
        if "dashboard" in requirement:
            self.assertIn('kanban', view_types)
    
    def test_menu_action_generation(self):
        """Test menu action generation"""
        requirement = "I need an inventory management system"
        
        spec = self.parser.parse_requirements(requirement)
        
        self.assertTrue(len(spec.menu_actions) > 0)
        
        # Each model should have a corresponding menu action
        model_names = [model.name for model in spec.models]
        action_models = [action.model for action in spec.menu_actions]
        
        for model_name in model_names:
            self.assertIn(model_name, action_models)
    
    def test_field_type_mapping(self):
        """Test correct field type assignment"""
        requirement = "Track employee data with name, salary, hire date, and active status"
        
        spec = self.parser.parse_requirements(requirement)
        
        if spec.models:
            model = spec.models[0]
            field_types = {field.name: field.field_type for field in model.fields}
            
            # Check specific field type mappings
            if 'name' in field_types:
                self.assertEqual(field_types['name'], FieldType.CHAR)
            if 'salary' in field_types or any('amount' in fname for fname in field_types):
                amount_fields = [ft for fname, ft in field_types.items() 
                               if 'amount' in fname or 'salary' in fname]
                if amount_fields:
                    self.assertIn(amount_fields[0], [FieldType.FLOAT, FieldType.MONETARY])
            if 'active' in field_types:
                self.assertEqual(field_types['active'], FieldType.BOOLEAN)
    
    def test_empty_requirement(self):
        """Test handling of empty requirement"""
        spec = self.parser.parse_requirements("")
        
        self.assertIsInstance(spec, ModuleSpec)
        self.assertTrue(spec.name)  # Should have some default name
    
    def test_complex_requirement(self):
        """Test parsing of complex requirement with multiple entities and relationships"""
        requirement = """
        I need a comprehensive CRM system that manages customers, leads, opportunities, 
        and sales orders. Customers should have contact information and lead history. 
        Opportunities should be linked to customers and have status tracking. 
        The system should include a dashboard showing sales performance.
        """
        
        spec = self.parser.parse_requirements(requirement)
        
        # Should identify multiple entities
        model_names = [model.name.lower() for model in spec.models]
        expected_entities = ['customer', 'lead', 'opportunity', 'sales']
        
        found_entities = []
        for entity in expected_entities:
            if any(entity in name for name in model_names):
                found_entities.append(entity)
        
        self.assertTrue(len(found_entities) >= 2)  # Should find at least 2 entities
        
        # Should include dashboard view
        view_types = [view.view_type for view in spec.views]
        self.assertTrue('kanban' in view_types or 'graph' in view_types)
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary"""
        requirement = "Simple inventory tracking"
        spec = self.parser.parse_requirements(requirement)
        
        spec_dict = self.parser.to_dict(spec)
        
        self.assertIsInstance(spec_dict, dict)
        self.assertIn('name', spec_dict)
        self.assertIn('models', spec_dict)
        self.assertIn('views', spec_dict)
    
    def test_from_dict_conversion(self):
        """Test conversion from dictionary"""
        requirement = "Simple task management"
        original_spec = self.parser.parse_requirements(requirement)
        
        spec_dict = self.parser.to_dict(original_spec)
        reconstructed_spec = self.parser.from_dict(spec_dict)
        
        self.assertEqual(original_spec.name, reconstructed_spec.name)
        self.assertEqual(len(original_spec.models), len(reconstructed_spec.models))


if __name__ == '__main__':
    unittest.main()