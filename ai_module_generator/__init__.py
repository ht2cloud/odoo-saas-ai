"""
AI Module Generator for Odoo SaaS Platform

This package provides AI-driven automation for Odoo module creation and configuration.
It enables users to describe requirements in natural language and instantly deploy
custom Odoo solutions.
"""

__version__ = "0.1.0"
__author__ = "HT2Cloud"
__email__ = "contact@ht2cloud.com"

from .nlp_parser import NLPParser
from .code_generator import CodeGenerator
from .integration import OdooIntegration
from .config_engine import ConfigurationEngine
from .feedback import FeedbackCollector
from .security import SecurityAnalyzer

__all__ = [
    "NLPParser",
    "CodeGenerator", 
    "OdooIntegration",
    "ConfigurationEngine",
    "FeedbackCollector",
    "SecurityAnalyzer",
]