"""
Intelligent Configuration Engine

Suggests optimal settings per use-case and manages workflows, 
permissions, and business logic.
"""

import json
import yaml
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .nlp_parser import ModuleSpec, Model, Field, FieldType


class AccessLevel(Enum):
    """User access levels"""
    READ_ONLY = "readonly"
    READ_WRITE = "readwrite"
    ADMIN = "admin"
    CUSTOM = "custom"


class WorkflowState(Enum):
    """Common workflow states"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class SecurityRule:
    """Security access rule configuration"""
    name: str
    model: str
    groups: List[str]
    domain: Optional[str] = None
    permissions: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {
                "read": True,
                "write": False,
                "create": False,
                "unlink": False
            }


@dataclass
class WorkflowConfig:
    """Workflow configuration"""
    name: str
    model: str
    states: List[WorkflowState]
    transitions: Dict[str, List[str]]  # state -> list of next states
    field_name: str = "state"


@dataclass
class ModuleConfiguration:
    """Complete module configuration"""
    module_spec: ModuleSpec
    security_rules: List[SecurityRule]
    workflows: List[WorkflowConfig]
    menu_structure: Dict[str, Any]
    default_values: Dict[str, Dict[str, Any]]
    business_rules: List[Dict[str, Any]]


class ConfigurationEngine:
    """
    Intelligent engine for generating optimal Odoo module configurations
    based on business requirements and best practices.
    """
    
    def __init__(self):
        """Initialize the configuration engine"""
        self.industry_templates = self._load_industry_templates()
        self.security_patterns = self._load_security_patterns()
        self.workflow_patterns = self._load_workflow_patterns()
    
    def generate_configuration(self, spec: ModuleSpec, 
                             industry: Optional[str] = None,
                             user_requirements: Optional[Dict] = None) -> ModuleConfiguration:
        """
        Generate complete module configuration based on specifications.
        
        Args:
            spec: Module specification
            industry: Industry type for specialized configurations
            user_requirements: Additional user requirements
            
        Returns:
            Complete module configuration
        """
        # Generate security rules
        security_rules = self._generate_security_rules(spec, user_requirements)
        
        # Generate workflows
        workflows = self._generate_workflows(spec, industry)
        
        # Generate menu structure
        menu_structure = self._generate_menu_structure(spec)
        
        # Generate default values
        default_values = self._generate_default_values(spec)
        
        # Generate business rules
        business_rules = self._generate_business_rules(spec, industry)
        
        return ModuleConfiguration(
            module_spec=spec,
            security_rules=security_rules,
            workflows=workflows,
            menu_structure=menu_structure,
            default_values=default_values,
            business_rules=business_rules
        )
    
    def _generate_security_rules(self, spec: ModuleSpec, 
                               user_requirements: Optional[Dict] = None) -> List[SecurityRule]:
        """Generate security access rules"""
        rules = []
        
        for model in spec.models:
            # Default rule for all users
            default_rule = SecurityRule(
                name=f"access_{model.name.replace('.', '_')}_user",
                model=model.name,
                groups=["base.group_user"],
                permissions={
                    "read": True,
                    "write": True,
                    "create": True,
                    "unlink": False
                }
            )
            rules.append(default_rule)
            
            # Manager rule for full access
            manager_rule = SecurityRule(
                name=f"access_{model.name.replace('.', '_')}_manager",
                model=model.name,
                groups=["base.group_system"],
                permissions={
                    "read": True,
                    "write": True,
                    "create": True,
                    "unlink": True
                }
            )
            rules.append(manager_rule)
            
            # Check for sensitive data and create restricted rules
            if self._has_sensitive_data(model):
                sensitive_rule = SecurityRule(
                    name=f"access_{model.name.replace('.', '_')}_restricted",
                    model=model.name,
                    groups=["base.group_user"],
                    domain="[('create_uid', '=', user.id)]",  # Only own records
                    permissions={
                        "read": True,
                        "write": True,
                        "create": True,
                        "unlink": False
                    }
                )
                rules.append(sensitive_rule)
        
        return rules
    
    def _generate_workflows(self, spec: ModuleSpec, 
                          industry: Optional[str] = None) -> List[WorkflowConfig]:
        """Generate workflow configurations"""
        workflows = []
        
        for model in spec.models:
            # Check if model needs a workflow
            if self._needs_workflow(model):
                workflow = self._create_workflow_for_model(model, industry)
                if workflow:
                    workflows.append(workflow)
        
        return workflows
    
    def _generate_menu_structure(self, spec: ModuleSpec) -> Dict[str, Any]:
        """Generate optimized menu structure"""
        structure = {
            "main_menu": {
                "name": spec.display_name,
                "sequence": 10,
                "submenus": []
            }
        }
        
        # Group models by category
        model_categories = self._categorize_models(spec.models)
        
        sequence = 10
        for category, models in model_categories.items():
            if len(models) == 1:
                # Single model - add directly to main menu
                structure["main_menu"]["submenus"].append({
                    "name": models[0].description,
                    "model": models[0].name,
                    "sequence": sequence
                })
            else:
                # Multiple models - create submenu
                submenu = {
                    "name": category,
                    "sequence": sequence,
                    "submenus": []
                }
                
                for i, model in enumerate(models):
                    submenu["submenus"].append({
                        "name": model.description,
                        "model": model.name,
                        "sequence": (i + 1) * 10
                    })
                
                structure["main_menu"]["submenus"].append(submenu)
            
            sequence += 10
        
        return structure
    
    def _generate_default_values(self, spec: ModuleSpec) -> Dict[str, Dict[str, Any]]:
        """Generate smart default values for fields"""
        defaults = {}
        
        for model in spec.models:
            model_defaults = {}
            
            for field in model.fields:
                default_value = self._suggest_default_value(field, model)
                if default_value is not None:
                    model_defaults[field.name] = default_value
            
            if model_defaults:
                defaults[model.name] = model_defaults
        
        return defaults
    
    def _generate_business_rules(self, spec: ModuleSpec, 
                               industry: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate business logic rules"""
        rules = []
        
        for model in spec.models:
            # Generate validation rules
            validation_rules = self._generate_validation_rules(model)
            rules.extend(validation_rules)
            
            # Generate compute rules
            compute_rules = self._generate_compute_rules(model)
            rules.extend(compute_rules)
            
            # Generate automation rules
            automation_rules = self._generate_automation_rules(model, industry)
            rules.extend(automation_rules)
        
        return rules
    
    def _has_sensitive_data(self, model: Model) -> bool:
        """Check if model contains sensitive data"""
        sensitive_keywords = [
            'salary', 'wage', 'payment', 'bank', 'ssn', 'social_security',
            'passport', 'id_number', 'personal', 'private', 'confidential'
        ]
        
        model_text = f"{model.name} {model.description}".lower()
        field_text = " ".join([f.name for f in model.fields]).lower()
        
        all_text = f"{model_text} {field_text}"
        
        return any(keyword in all_text for keyword in sensitive_keywords)
    
    def _needs_workflow(self, model: Model) -> bool:
        """Determine if model needs a workflow"""
        workflow_indicators = [
            'approval', 'request', 'application', 'order', 'invoice',
            'proposal', 'contract', 'document', 'ticket', 'task'
        ]
        
        model_text = f"{model.name} {model.description}".lower()
        
        # Check if model has status/state field
        has_state_field = any(f.name in ['state', 'status'] for f in model.fields)
        
        # Check for workflow indicators
        has_workflow_indicator = any(indicator in model_text for indicator in workflow_indicators)
        
        return has_state_field or has_workflow_indicator
    
    def _create_workflow_for_model(self, model: Model, 
                                 industry: Optional[str] = None) -> Optional[WorkflowConfig]:
        """Create workflow configuration for a model"""
        model_type = self._classify_model_type(model)
        
        if model_type == "approval":
            return WorkflowConfig(
                name=f"{model.name}_workflow",
                model=model.name,
                states=[
                    WorkflowState.DRAFT,
                    WorkflowState.SUBMITTED,
                    WorkflowState.APPROVED,
                    WorkflowState.REJECTED
                ],
                transitions={
                    "draft": ["submitted"],
                    "submitted": ["approved", "rejected"],
                    "approved": [],
                    "rejected": ["draft"]
                }
            )
        
        elif model_type == "task":
            return WorkflowConfig(
                name=f"{model.name}_workflow",
                model=model.name,
                states=[
                    WorkflowState.DRAFT,
                    WorkflowState.SUBMITTED,
                    WorkflowState.DONE,
                    WorkflowState.CANCELLED
                ],
                transitions={
                    "draft": ["submitted", "cancelled"],
                    "submitted": ["done", "cancelled"],
                    "done": [],
                    "cancelled": ["draft"]
                }
            )
        
        return None
    
    def _classify_model_type(self, model: Model) -> str:
        """Classify model type for workflow generation"""
        model_text = f"{model.name} {model.description}".lower()
        
        if any(word in model_text for word in ['approval', 'request', 'application']):
            return "approval"
        elif any(word in model_text for word in ['task', 'ticket', 'issue']):
            return "task"
        elif any(word in model_text for word in ['order', 'purchase', 'sale']):
            return "transaction"
        else:
            return "basic"
    
    def _categorize_models(self, models: List[Model]) -> Dict[str, List[Model]]:
        """Categorize models for menu organization"""
        categories = {}
        
        for model in models:
            category = self._get_model_category(model)
            if category not in categories:
                categories[category] = []
            categories[category].append(model)
        
        return categories
    
    def _get_model_category(self, model: Model) -> str:
        """Get category for a model"""
        model_text = f"{model.name} {model.description}".lower()
        
        if any(word in model_text for word in ['sale', 'customer', 'lead', 'crm']):
            return "Sales"
        elif any(word in model_text for word in ['purchase', 'vendor', 'supplier']):
            return "Purchase"
        elif any(word in model_text for word in ['inventory', 'stock', 'product']):
            return "Inventory"
        elif any(word in model_text for word in ['hr', 'employee', 'payroll']):
            return "Human Resources"
        elif any(word in model_text for word in ['account', 'invoice', 'payment']):
            return "Accounting"
        elif any(word in model_text for word in ['project', 'task', 'timesheet']):
            return "Project"
        else:
            return "Operations"
    
    def _suggest_default_value(self, field: Field, model: Model) -> Any:
        """Suggest default value for a field"""
        if field.name == "active":
            return True
        elif field.name == "state" or field.name == "status":
            return "draft"
        elif field.field_type == FieldType.DATE:
            return "fields.Date.today()"
        elif field.field_type == FieldType.DATETIME:
            return "fields.Datetime.now()"
        elif field.field_type == FieldType.BOOLEAN:
            return False
        elif field.field_type == FieldType.INTEGER:
            if "sequence" in field.name:
                return 10
            elif "priority" in field.name:
                return 1
        
        return None
    
    def _generate_validation_rules(self, model: Model) -> List[Dict[str, Any]]:
        """Generate validation rules for a model"""
        rules = []
        
        for field in model.fields:
            if field.field_type == FieldType.CHAR and "email" in field.name:
                rules.append({
                    "type": "constraint",
                    "model": model.name,
                    "field": field.name,
                    "constraint": "email_validation",
                    "message": "Please enter a valid email address"
                })
            
            elif field.field_type in [FieldType.INTEGER, FieldType.FLOAT] and "amount" in field.name:
                rules.append({
                    "type": "constraint",
                    "model": model.name,
                    "field": field.name,
                    "constraint": "positive_amount",
                    "message": "Amount must be positive"
                })
        
        return rules
    
    def _generate_compute_rules(self, model: Model) -> List[Dict[str, Any]]:
        """Generate computed field rules"""
        rules = []
        
        # Look for fields that could be computed
        for field in model.fields:
            if field.name == "total" or field.name == "amount_total":
                rules.append({
                    "type": "compute",
                    "model": model.name,
                    "field": field.name,
                    "depends": ["amount", "quantity"],
                    "function": "_compute_total"
                })
        
        return rules
    
    def _generate_automation_rules(self, model: Model, 
                                 industry: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate automation rules"""
        rules = []
        
        # Email notifications for workflow changes
        if any(f.name in ['state', 'status'] for f in model.fields):
            rules.append({
                "type": "automation",
                "model": model.name,
                "trigger": "state_change",
                "action": "send_notification",
                "condition": "state == 'submitted'",
                "message": "New submission requires approval"
            })
        
        return rules
    
    def _load_industry_templates(self) -> Dict[str, Any]:
        """Load industry-specific configuration templates"""
        # In a real implementation, this would load from external files
        return {
            "manufacturing": {
                "workflows": ["quality_control", "production_planning"],
                "security": "strict",
                "automation": ["inventory_alerts", "production_scheduling"]
            },
            "retail": {
                "workflows": ["order_fulfillment", "returns"],
                "security": "standard",
                "automation": ["stock_reordering", "customer_notifications"]
            },
            "healthcare": {
                "workflows": ["patient_intake", "treatment_approval"],
                "security": "high",
                "automation": ["appointment_reminders", "compliance_checks"]
            }
        }
    
    def _load_security_patterns(self) -> Dict[str, Any]:
        """Load security configuration patterns"""
        return {
            "financial": {
                "rules": ["owner_only", "manager_approval"],
                "encryption": ["amount_fields", "account_numbers"]
            },
            "hr": {
                "rules": ["department_isolation", "manager_hierarchy"],
                "encryption": ["salary_fields", "personal_info"]
            }
        }
    
    def _load_workflow_patterns(self) -> Dict[str, Any]:
        """Load workflow configuration patterns"""
        return {
            "approval": {
                "states": ["draft", "submitted", "approved", "rejected"],
                "transitions": {"draft": ["submitted"], "submitted": ["approved", "rejected"]}
            },
            "fulfillment": {
                "states": ["draft", "confirmed", "processing", "shipped", "delivered"],
                "transitions": {
                    "draft": ["confirmed"],
                    "confirmed": ["processing"],
                    "processing": ["shipped"],
                    "shipped": ["delivered"]
                }
            }
        }
    
    def export_configuration(self, config: ModuleConfiguration, 
                           format: str = "json") -> str:
        """
        Export configuration to various formats.
        
        Args:
            config: Module configuration
            format: Export format ('json', 'yaml')
            
        Returns:
            Serialized configuration
        """
        config_dict = asdict(config)
        
        if format == "json":
            return json.dumps(config_dict, indent=2, default=str)
        elif format == "yaml":
            return yaml.dump(config_dict, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_configuration(self, config_data: str, 
                           format: str = "json") -> ModuleConfiguration:
        """
        Import configuration from serialized data.
        
        Args:
            config_data: Serialized configuration data
            format: Data format ('json', 'yaml')
            
        Returns:
            Module configuration
        """
        if format == "json":
            config_dict = json.loads(config_data)
        elif format == "yaml":
            config_dict = yaml.safe_load(config_data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Convert back to proper objects
        # This would need more sophisticated deserialization in practice
        return ModuleConfiguration(**config_dict)