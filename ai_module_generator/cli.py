"""
Command Line Interface for AI Module Generator

Provides command-line access to the AI-driven Odoo module generation system.
"""

import os
import sys
import argparse
import json
import logging
from typing import Optional, Dict, Any

from .nlp_parser import NLPParser
from .code_generator import CodeGenerator
from .integration import OdooIntegration, OdooConnection
from .config_engine import ConfigurationEngine
from .feedback import FeedbackCollector, FeedbackEntry, FeedbackType, Rating
from .security import SecurityAnalyzer


def setup_logging(verbose: bool = False):
    """Set up logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def generate_module_command(args):
    """Handle module generation command"""
    try:
        # Parse requirements
        parser = NLPParser()
        spec = parser.parse_requirements(args.requirements)
        
        print(f"Generated specification for module: {spec.name}")
        print(f"Description: {spec.description}")
        print(f"Models: {len(spec.models)}")
        print(f"Views: {len(spec.views)}")
        
        # Generate configuration if requested
        if args.configure:
            config_engine = ConfigurationEngine()
            compliance_frameworks = []
            if args.gdpr:
                compliance_frameworks.append("gdpr")
            if args.hipaa:
                compliance_frameworks.append("hipaa")
            
            config = config_engine.generate_configuration(
                spec, 
                industry=args.industry,
                user_requirements={'compliance_frameworks': compliance_frameworks}
            )
            print(f"Generated configuration with {len(config.security_rules)} security rules")
        
        # Generate code
        generator = CodeGenerator()
        generated_files = generator.generate_module(spec, args.output_dir)
        
        print(f"Generated {len(generated_files)} files in {args.output_dir}")
        
        # Security analysis if requested
        if args.security_scan:
            analyzer = SecurityAnalyzer()
            scan_result = analyzer.analyze_module(spec, generated_files)
            
            print(f"\nSecurity Scan Results:")
            print(f"Overall Score: {scan_result.overall_score:.1f}/100")
            print(f"Status: {'PASSED' if scan_result.passed else 'FAILED'}")
            print(f"Security Issues: {len(scan_result.security_issues)}")
            print(f"Compliance Issues: {len(scan_result.compliance_issues)}")
            
            if args.security_report:
                report = analyzer.generate_security_report(scan_result)
                with open(args.security_report, 'w') as f:
                    f.write(report)
                print(f"Security report saved to {args.security_report}")
        
        # Deploy if requested
        if args.deploy and args.odoo_config:
            with open(args.odoo_config, 'r') as f:
                config_data = json.load(f)
            
            connection = OdooConnection(**config_data)
            integration = OdooIntegration(connection)
            
            if integration.connect():
                success, message = integration.deploy_and_install(
                    os.path.join(args.output_dir, spec.name),
                    args.addons_path or "/opt/odoo/addons"
                )
                print(f"Deployment: {message}")
            else:
                print("Failed to connect to Odoo instance")
        
        print(f"\nModule generation completed successfully!")
        
    except Exception as e:
        print(f"Error generating module: {e}")
        sys.exit(1)


def analyze_feedback_command(args):
    """Handle feedback analysis command"""
    try:
        collector = FeedbackCollector(args.db_path)
        
        if args.module:
            summary = collector.get_feedback_summary(args.module, args.days)
            print(f"Feedback Summary for {args.module} (last {args.days} days):")
        else:
            summary = collector.get_feedback_summary(days=args.days)
            print(f"Overall Feedback Summary (last {args.days} days):")
        
        print(f"Total Feedback: {summary.get('total_feedback', 0)}")
        print(f"Average Rating: {summary.get('average_rating', 0):.2f}")
        
        rating_dist = summary.get('rating_distribution', {})
        if rating_dist:
            print("\nRating Distribution:")
            for rating, count in sorted(rating_dist.items()):
                print(f"  {rating} stars: {count}")
        
        feedback_types = summary.get('feedback_by_type', {})
        if feedback_types:
            print("\nFeedback by Type:")
            for ftype, count in feedback_types.items():
                print(f"  {ftype}: {count}")
        
        # Generate insights
        if args.insights:
            insights = collector.analyze_feedback_patterns(args.module)
            if insights:
                print(f"\nLearning Insights ({len(insights)} found):")
                for insight in insights:
                    print(f"  [{insight.priority.upper()}] {insight.category}: {insight.description}")
                    print(f"    Confidence: {insight.confidence:.2f}")
                    print(f"    Recommendations: {', '.join(insight.recommendations[:2])}...")
                    print()
        
    except Exception as e:
        print(f"Error analyzing feedback: {e}")
        sys.exit(1)


def submit_feedback_command(args):
    """Handle feedback submission command"""
    try:
        collector = FeedbackCollector(args.db_path)
        
        feedback_type = FeedbackType(args.type)
        rating = Rating(args.rating) if args.rating else None
        
        feedback = FeedbackEntry(
            user_id=args.user_id,
            module_name=args.module,
            feedback_type=feedback_type,
            rating=rating,
            content=args.content or "",
            metadata={"cli_submission": True}
        )
        
        if collector.collect_feedback(feedback):
            print("Feedback submitted successfully!")
        else:
            print("Failed to submit feedback")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        sys.exit(1)


def test_connection_command(args):
    """Handle Odoo connection testing"""
    try:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        
        connection = OdooConnection(**config_data)
        integration = OdooIntegration(connection)
        
        print(f"Testing connection to {connection.full_url}...")
        
        if integration.connect():
            print("✓ Connection successful!")
            
            if integration.test_connection():
                print("✓ API access confirmed!")
                
                # Get some basic info
                databases = integration.get_database_list()
                print(f"✓ Available databases: {len(databases)}")
                
                modules = integration.get_installed_modules()
                print(f"✓ Installed modules: {len(modules)}")
                
            else:
                print("✗ API access failed")
                sys.exit(1)
        else:
            print("✗ Connection failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error testing connection: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AI-Driven Odoo Module Generator",
        prog="odoo-ai-generator"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate module command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate Odoo module from requirements"
    )
    generate_parser.add_argument(
        "requirements",
        help="Natural language requirements for the module"
    )
    generate_parser.add_argument(
        "-o", "--output-dir",
        default="generated_modules",
        help="Output directory for generated module"
    )
    generate_parser.add_argument(
        "--configure",
        action="store_true",
        help="Generate advanced configuration"
    )
    generate_parser.add_argument(
        "--industry",
        choices=["manufacturing", "retail", "healthcare", "finance"],
        help="Industry-specific optimizations"
    )
    generate_parser.add_argument(
        "--gdpr",
        action="store_true",
        help="Enable GDPR compliance checks"
    )
    generate_parser.add_argument(
        "--hipaa",
        action="store_true",
        help="Enable HIPAA compliance checks"
    )
    generate_parser.add_argument(
        "--security-scan",
        action="store_true",
        help="Perform security analysis"
    )
    generate_parser.add_argument(
        "--security-report",
        help="Save security report to file"
    )
    generate_parser.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy module after generation"
    )
    generate_parser.add_argument(
        "--odoo-config",
        help="Odoo connection configuration file (JSON)"
    )
    generate_parser.add_argument(
        "--addons-path",
        help="Odoo addons directory path"
    )
    generate_parser.set_defaults(func=generate_module_command)
    
    # Feedback analysis command
    feedback_parser = subparsers.add_parser(
        "feedback",
        help="Analyze collected feedback"
    )
    feedback_parser.add_argument(
        "--db-path",
        default="feedback.db",
        help="Path to feedback database"
    )
    feedback_parser.add_argument(
        "--module",
        help="Analyze feedback for specific module"
    )
    feedback_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze"
    )
    feedback_parser.add_argument(
        "--insights",
        action="store_true",
        help="Generate learning insights"
    )
    feedback_parser.set_defaults(func=analyze_feedback_command)
    
    # Submit feedback command
    submit_parser = subparsers.add_parser(
        "submit-feedback",
        help="Submit feedback for a module"
    )
    submit_parser.add_argument(
        "module",
        help="Module name"
    )
    submit_parser.add_argument(
        "user_id",
        help="User ID"
    )
    submit_parser.add_argument(
        "--type",
        choices=["rating", "suggestion", "bug_report", "feature_request"],
        default="rating",
        help="Type of feedback"
    )
    submit_parser.add_argument(
        "--rating",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Rating (1-5 stars)"
    )
    submit_parser.add_argument(
        "--content",
        help="Feedback content/message"
    )
    submit_parser.add_argument(
        "--db-path",
        default="feedback.db",
        help="Path to feedback database"
    )
    submit_parser.set_defaults(func=submit_feedback_command)
    
    # Test connection command
    test_parser = subparsers.add_parser(
        "test-connection",
        help="Test connection to Odoo instance"
    )
    test_parser.add_argument(
        "config",
        help="Odoo connection configuration file (JSON)"
    )
    test_parser.set_defaults(func=test_connection_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Execute command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()