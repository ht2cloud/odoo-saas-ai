"""
NLP Requirement Parser

Parses user stories and business needs in plain language and outputs 
structured technical specifications for Odoo modules.
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class FieldType(Enum):
    """Supported Odoo field types"""
    CHAR = "char"
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    SELECTION = "selection"
    MANY2ONE = "many2one"
    ONE2MANY = "one2many"
    MANY2MANY = "many2many"
    BINARY = "binary"
    HTML = "html"
    MONETARY = "monetary"


@dataclass
class Field:
    """Represents an Odoo model field"""
    name: str
    field_type: FieldType
    string: str
    required: bool = False
    readonly: bool = False
    help: Optional[str] = None
    default: Optional[Any] = None
    domain: Optional[str] = None
    relation: Optional[str] = None
    selection_options: Optional[List[tuple]] = None


@dataclass
class Model:
    """Represents an Odoo model"""
    name: str
    description: str
    table_name: str
    fields: List[Field]
    inherit: Optional[str] = None
    rec_name: Optional[str] = None
    order: Optional[str] = None


@dataclass
class View:
    """Represents an Odoo view"""
    name: str
    model: str
    view_type: str  # form, tree, kanban, calendar, graph, pivot, search
    arch: str
    priority: int = 16


@dataclass
class MenuAction:
    """Represents an Odoo menu action"""
    name: str
    model: str
    view_mode: str
    domain: Optional[str] = None
    context: Optional[Dict] = None


@dataclass
class ModuleSpec:
    """Complete specification for an Odoo module"""
    name: str
    display_name: str
    description: str
    version: str = "1.0.0"
    author: str = "AI Module Generator"
    category: str = "Custom"
    depends: List[str] = None
    models: List[Model] = None
    views: List[View] = None
    menu_actions: List[MenuAction] = None
    
    def __post_init__(self):
        if self.depends is None:
            self.depends = ["base"]
        if self.models is None:
            self.models = []
        if self.views is None:
            self.views = []
        if self.menu_actions is None:
            self.menu_actions = []


class NLPParser:
    """
    Natural Language Processing parser for converting user requirements
    into structured Odoo module specifications.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the NLP parser.
        
        Args:
            api_key: Optional API key for external NLP services
        """
        self.api_key = api_key
        self._business_entities = {
            'sales', 'customer', 'lead', 'revenue', 'order', 'invoice', 
            'product', 'inventory', 'stock', 'purchase', 'vendor',
            'employee', 'hr', 'payroll', 'project', 'task', 'timesheet',
            'account', 'payment', 'expense', 'budget', 'report',
            'dashboard', 'analytics', 'crm', 'marketing', 'campaign'
        }
        
        self._field_keywords = {
            'name': (FieldType.CHAR, True),
            'title': (FieldType.CHAR, True),
            'description': (FieldType.TEXT, False),
            'amount': (FieldType.MONETARY, False),
            'price': (FieldType.FLOAT, False),
            'quantity': (FieldType.INTEGER, False),
            'date': (FieldType.DATE, False),
            'datetime': (FieldType.DATETIME, False),
            'active': (FieldType.BOOLEAN, False),
            'email': (FieldType.CHAR, False),
            'phone': (FieldType.CHAR, False),
            'address': (FieldType.TEXT, False),
            'notes': (FieldType.TEXT, False),
            'status': (FieldType.SELECTION, False),
            'state': (FieldType.SELECTION, False),
        }
    
    def parse_requirements(self, user_input: str) -> ModuleSpec:
        """
        Parse natural language requirements into structured module specification.
        
        Args:
            user_input: Natural language description of requirements
            
        Returns:
            ModuleSpec: Structured specification for the Odoo module
        """
        # Clean and normalize input
        user_input = self._clean_input(user_input)
        
        # Extract key information
        entities = self._extract_business_entities(user_input)
        relationships = self._identify_relationships(user_input, entities)
        views_needed = self._identify_views(user_input)
        
        # Generate module specification
        module_name = self._generate_module_name(entities)
        models = self._generate_models(entities, relationships, user_input)
        views = self._generate_views(models, views_needed)
        menu_actions = self._generate_menu_actions(models, views)
        
        return ModuleSpec(
            name=module_name,
            display_name=self._generate_display_name(entities),
            description=self._generate_description(user_input),
            models=models,
            views=views,
            menu_actions=menu_actions
        )
    
    def _clean_input(self, text: str) -> str:
        """Clean and normalize input text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        return text.lower()
    
    def _extract_business_entities(self, text: str) -> List[str]:
        """Extract business entities from text"""
        entities = []
        for entity in self._business_entities:
            if entity in text or f"{entity}s" in text:
                entities.append(entity)
        
        # Look for custom entities (nouns that might be business objects)
        words = text.split()
        for i, word in enumerate(words):
            if word.endswith('s') and len(word) > 3:
                singular = word[:-1]
                if singular not in self._business_entities and singular not in entities:
                    # Simple heuristic: if it appears with verbs like "track", "manage", "create"
                    context = ' '.join(words[max(0, i-2):min(len(words), i+3)])
                    if any(verb in context for verb in ['track', 'manage', 'create', 'store', 'handle']):
                        entities.append(singular)
        
        return list(set(entities))
    
    def _identify_relationships(self, text: str, entities: List[str]) -> Dict[str, List[str]]:
        """Identify relationships between entities"""
        relationships = {}
        
        # Look for relationship keywords
        for i, entity in enumerate(entities):
            relationships[entity] = []
            for j, other_entity in enumerate(entities):
                if i != j:
                    # Look for relationship indicators
                    patterns = [
                        f"{entity}.*belongs.*{other_entity}",
                        f"{entity}.*has.*{other_entity}",
                        f"{entity}.*contains.*{other_entity}",
                        f"{other_entity}.*of.*{entity}",
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, text):
                            relationships[entity].append(other_entity)
        
        return relationships
    
    def _identify_views(self, text: str) -> List[str]:
        """Identify what types of views are needed"""
        views = ['form', 'tree']  # Always include form and tree views
        
        view_keywords = {
            'dashboard': 'kanban',
            'chart': 'graph', 
            'graph': 'graph',
            'calendar': 'calendar',
            'pivot': 'pivot',
            'report': 'graph'
        }
        
        for keyword, view_type in view_keywords.items():
            if keyword in text and view_type not in views:
                views.append(view_type)
        
        return views
    
    def _generate_module_name(self, entities: List[str]) -> str:
        """Generate module name from entities"""
        if not entities:
            return "custom_module"
        
        # Take the first main entity and create a module name
        main_entity = entities[0]
        return f"custom_{main_entity}_management"
    
    def _generate_display_name(self, entities: List[str]) -> str:
        """Generate human-readable display name"""
        if not entities:
            return "Custom Module"
        
        main_entity = entities[0].title()
        return f"{main_entity} Management"
    
    def _generate_description(self, user_input: str) -> str:
        """Generate module description"""
        return f"AI-generated module based on requirements: {user_input[:100]}..."
    
    def _generate_models(self, entities: List[str], relationships: Dict[str, List[str]], 
                        user_input: str) -> List[Model]:
        """Generate Odoo models from entities"""
        models = []
        
        for entity in entities:
            # Generate fields for this entity
            fields = self._generate_fields_for_entity(entity, relationships.get(entity, []), user_input)
            
            model = Model(
                name=f"custom.{entity}",
                description=f"{entity.title()} Management",
                table_name=f"custom_{entity}",
                fields=fields,
                rec_name="name"
            )
            models.append(model)
        
        return models
    
    def _generate_fields_for_entity(self, entity: str, related_entities: List[str], 
                                  user_input: str) -> List[Field]:
        """Generate fields for a specific entity"""
        fields = []
        
        # Always add basic fields
        fields.append(Field(
            name="name",
            field_type=FieldType.CHAR,
            string="Name",
            required=True
        ))
        
        fields.append(Field(
            name="description",
            field_type=FieldType.TEXT,
            string="Description"
        ))
        
        fields.append(Field(
            name="active",
            field_type=FieldType.BOOLEAN,
            string="Active",
            default=True
        ))
        
        # Add entity-specific fields based on keywords
        for keyword, (field_type, required) in self._field_keywords.items():
            if keyword in user_input and keyword != "name":  # name already added
                if keyword == "status" or keyword == "state":
                    fields.append(Field(
                        name=keyword,
                        field_type=field_type,
                        string=keyword.title(),
                        required=required,
                        selection_options=[('draft', 'Draft'), ('active', 'Active'), ('done', 'Done')]
                    ))
                else:
                    fields.append(Field(
                        name=keyword,
                        field_type=field_type,
                        string=keyword.title(),
                        required=required
                    ))
        
        # Add relationship fields
        for related_entity in related_entities:
            fields.append(Field(
                name=f"{related_entity}_id",
                field_type=FieldType.MANY2ONE,
                string=related_entity.title(),
                relation=f"custom.{related_entity}"
            ))
        
        return fields
    
    def _generate_views(self, models: List[Model], view_types: List[str]) -> List[View]:
        """Generate views for the models"""
        views = []
        
        for model in models:
            for view_type in view_types:
                if view_type in ['form', 'tree']:
                    arch = self._generate_basic_view_arch(model, view_type)
                    view = View(
                        name=f"{model.name.replace('.', '_')}_{view_type}_view",
                        model=model.name,
                        view_type=view_type,
                        arch=arch
                    )
                    views.append(view)
        
        return views
    
    def _generate_basic_view_arch(self, model: Model, view_type: str) -> str:
        """Generate basic view architecture"""
        if view_type == "form":
            field_elements = "\n".join([f'                    <field name="{field.name}"/>' 
                                       for field in model.fields[:5]])  # Limit to first 5 fields
            return f'''<form>
                <sheet>
                    <group>
{field_elements}
                    </group>
                </sheet>
            </form>'''
        
        elif view_type == "tree":
            field_elements = "\n".join([f'                <field name="{field.name}"/>' 
                                       for field in model.fields[:3]])  # Limit to first 3 fields
            return f'''<tree>
{field_elements}
            </tree>'''
        
        return "<tree/>"
    
    def _generate_menu_actions(self, models: List[Model], views: List[View]) -> List[MenuAction]:
        """Generate menu actions for the models"""
        actions = []
        
        for model in models:
            # Get view modes for this model
            view_modes = []
            for view in views:
                if view.model == model.name and view.view_type not in view_modes:
                    view_modes.append(view.view_type)
            
            if view_modes:
                action = MenuAction(
                    name=model.description,
                    model=model.name,
                    view_mode=",".join(view_modes)
                )
                actions.append(action)
        
        return actions
    
    def to_dict(self, spec: ModuleSpec) -> Dict:
        """Convert ModuleSpec to dictionary"""
        return asdict(spec)
    
    def from_dict(self, data: Dict) -> ModuleSpec:
        """Create ModuleSpec from dictionary"""
        # Convert field types back to enum
        for model_data in data.get('models', []):
            for field_data in model_data.get('fields', []):
                if 'field_type' in field_data:
                    field_data['field_type'] = FieldType(field_data['field_type'])
        
        return ModuleSpec(**data)