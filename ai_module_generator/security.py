"""
Security & Compliance Analyzer

Scans generated code for security vulnerabilities and enforces business 
compliance requirements (GDPR, etc.).
"""

import re
import ast
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import xml.etree.ElementTree as ET

from .nlp_parser import ModuleSpec, Model, Field, FieldType


class VulnerabilityLevel(Enum):
    """Security vulnerability levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"


@dataclass
class SecurityIssue:
    """Security issue found in code"""
    issue_id: str
    severity: VulnerabilityLevel
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    recommendation: str = ""
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID
    owasp_category: Optional[str] = None


@dataclass
class ComplianceIssue:
    """Compliance issue found in code"""
    issue_id: str
    framework: ComplianceFramework
    requirement: str
    description: str
    file_path: str
    recommendation: str
    mandatory: bool = True


@dataclass
class SecurityScanResult:
    """Result of security scan"""
    module_name: str
    scan_timestamp: str
    security_issues: List[SecurityIssue]
    compliance_issues: List[ComplianceIssue]
    overall_score: float  # 0-100 security score
    passed: bool


class SecurityAnalyzer:
    """
    Analyzes generated Odoo modules for security vulnerabilities and 
    compliance issues.
    """
    
    def __init__(self):
        """Initialize security analyzer"""
        self.logger = logging.getLogger(__name__)
        self.security_rules = self._load_security_rules()
        self.compliance_rules = self._load_compliance_rules()
    
    def analyze_module(self, module_spec: ModuleSpec, 
                      generated_files: Dict[str, str],
                      compliance_frameworks: List[ComplianceFramework] = None) -> SecurityScanResult:
        """
        Perform comprehensive security analysis of generated module.
        
        Args:
            module_spec: Module specification
            generated_files: Dict of file paths to content
            compliance_frameworks: List of compliance frameworks to check
            
        Returns:
            Security scan result
        """
        if compliance_frameworks is None:
            compliance_frameworks = [ComplianceFramework.GDPR]
        
        security_issues = []
        compliance_issues = []
        
        # Analyze each generated file
        for file_path, content in generated_files.items():
            if file_path.endswith('.py'):
                security_issues.extend(self._analyze_python_file(file_path, content))
                
            elif file_path.endswith('.xml'):
                security_issues.extend(self._analyze_xml_file(file_path, content))
            
            elif file_path.endswith('.csv'):
                security_issues.extend(self._analyze_csv_file(file_path, content))
        
        # Check compliance requirements
        for framework in compliance_frameworks:
            compliance_issues.extend(
                self._check_compliance(module_spec, generated_files, framework)
            )
        
        # Calculate overall security score
        overall_score = self._calculate_security_score(security_issues, compliance_issues)
        
        # Determine if module passes security requirements
        passed = (
            len([i for i in security_issues if i.severity in [VulnerabilityLevel.HIGH, VulnerabilityLevel.CRITICAL]]) == 0 and
            len([i for i in compliance_issues if i.mandatory]) == 0
        )
        
        return SecurityScanResult(
            module_name=module_spec.name,
            scan_timestamp=str(datetime.now()),
            security_issues=security_issues,
            compliance_issues=compliance_issues,
            overall_score=overall_score,
            passed=passed
        )
    
    def _analyze_python_file(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Analyze Python file for security issues"""
        issues = []
        
        try:
            # Parse Python AST
            tree = ast.parse(content)
            
            # Check for various security issues
            issues.extend(self._check_sql_injection(file_path, content, tree))
            issues.extend(self._check_hardcoded_secrets(file_path, content))
            issues.extend(self._check_unsafe_eval(file_path, content, tree))
            issues.extend(self._check_unsafe_imports(file_path, content, tree))
            issues.extend(self._check_permission_issues(file_path, content))
            issues.extend(self._check_data_validation(file_path, content, tree))
            
        except SyntaxError as e:
            issues.append(SecurityIssue(
                issue_id="SYNTAX_ERROR",
                severity=VulnerabilityLevel.HIGH,
                title="Syntax Error in Python Code",
                description=f"Syntax error prevents security analysis: {e}",
                file_path=file_path,
                line_number=e.lineno,
                recommendation="Fix syntax errors before deployment"
            ))
        
        return issues
    
    def _analyze_xml_file(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Analyze XML file for security issues"""
        issues = []
        
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Check for XML security issues
            issues.extend(self._check_xml_injection(file_path, content))
            issues.extend(self._check_access_rights_xml(file_path, root))
            issues.extend(self._check_domain_security(file_path, root))
            
        except ET.ParseError as e:
            issues.append(SecurityIssue(
                issue_id="XML_PARSE_ERROR",
                severity=VulnerabilityLevel.MEDIUM,
                title="XML Parse Error",
                description=f"XML parsing error: {e}",
                file_path=file_path,
                recommendation="Fix XML syntax before deployment"
            ))
        
        return issues
    
    def _analyze_csv_file(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Analyze CSV file for security issues"""
        issues = []
        
        # Check for overly permissive access rights
        if "ir.model.access.csv" in file_path:
            issues.extend(self._check_access_rights_csv(file_path, content))
        
        return issues
    
    def _check_sql_injection(self, file_path: str, content: str, tree: ast.AST) -> List[SecurityIssue]:
        """Check for SQL injection vulnerabilities"""
        issues = []
        
        # Look for direct SQL queries
        sql_patterns = [
            r'cr\.execute\s*\(\s*["\'].*%s.*["\']',  # String formatting in queries
            r'cr\.execute\s*\(\s*.*\+.*\)',  # String concatenation
            r'self\._cr\.execute\s*\(\s*["\'].*%s.*["\']',
        ]
        
        for pattern in sql_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    issue_id="SQL_INJECTION",
                    severity=VulnerabilityLevel.HIGH,
                    title="Potential SQL Injection",
                    description="Direct SQL query with string formatting detected",
                    file_path=file_path,
                    line_number=line_num,
                    recommendation="Use parameterized queries or ORM methods",
                    cwe_id="CWE-89",
                    owasp_category="A03:2021 - Injection"
                ))
        
        return issues
    
    def _check_hardcoded_secrets(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Check for hardcoded secrets"""
        issues = []
        
        # Patterns for common secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded Password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API Key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded Secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded Token"),
            (r'["\'][0-9a-fA-F]{32,}["\']', "Potential Hash/Key"),
        ]
        
        for pattern, title in secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    issue_id="HARDCODED_SECRET",
                    severity=VulnerabilityLevel.CRITICAL,
                    title=title,
                    description=f"Hardcoded secret found: {match.group()}",
                    file_path=file_path,
                    line_number=line_num,
                    recommendation="Use environment variables or secure configuration",
                    cwe_id="CWE-798"
                ))
        
        return issues
    
    def _check_unsafe_eval(self, file_path: str, content: str, tree: ast.AST) -> List[SecurityIssue]:
        """Check for unsafe eval usage"""
        issues = []
        
        class EvalVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec']:
                    line_num = node.lineno
                    issues.append(SecurityIssue(
                        issue_id="UNSAFE_EVAL",
                        severity=VulnerabilityLevel.HIGH,
                        title="Unsafe eval/exec Usage",
                        description=f"Use of {node.func.id} function detected",
                        file_path=file_path,
                        line_number=line_num,
                        recommendation="Avoid eval/exec or validate input thoroughly",
                        cwe_id="CWE-95",
                        owasp_category="A03:2021 - Injection"
                    ))
                self.generic_visit(node)
        
        visitor = EvalVisitor()
        visitor.visit(tree)
        
        return issues
    
    def _check_unsafe_imports(self, file_path: str, content: str, tree: ast.AST) -> List[SecurityIssue]:
        """Check for potentially unsafe imports"""
        issues = []
        
        unsafe_modules = [
            'subprocess', 'os', 'sys', 'pickle', 'marshal', 'shelve'
        ]
        
        class ImportVisitor(ast.NodeVisitor):
            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name in unsafe_modules:
                        issues.append(SecurityIssue(
                            issue_id="UNSAFE_IMPORT",
                            severity=VulnerabilityLevel.MEDIUM,
                            title="Potentially Unsafe Import",
                            description=f"Import of potentially unsafe module: {alias.name}",
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation="Review usage and ensure proper input validation"
                        ))
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node):
                if node.module in unsafe_modules:
                    issues.append(SecurityIssue(
                        issue_id="UNSAFE_IMPORT",
                        severity=VulnerabilityLevel.MEDIUM,
                        title="Potentially Unsafe Import",
                        description=f"Import from potentially unsafe module: {node.module}",
                        file_path=file_path,
                        line_number=node.lineno,
                        recommendation="Review usage and ensure proper input validation"
                    ))
                self.generic_visit(node)
        
        visitor = ImportVisitor()
        visitor.visit(tree)
        
        return issues
    
    def _check_permission_issues(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Check for permission-related issues"""
        issues = []
        
        # Check for missing access decorators
        if re.search(r'def\s+\w+\s*\([^)]*\):', content):
            if not re.search(r'@api\.(model|multi)', content):
                # This is a basic check - in practice, you'd want more sophisticated analysis
                pass
        
        # Check for sudo() usage without justification
        sudo_matches = re.finditer(r'\.sudo\(\)', content)
        for match in sudo_matches:
            line_num = content[:match.start()].count('\n') + 1
            issues.append(SecurityIssue(
                issue_id="SUDO_USAGE",
                severity=VulnerabilityLevel.MEDIUM,
                title="Sudo Usage Detected",
                description="Use of sudo() bypasses access controls",
                file_path=file_path,
                line_number=line_num,
                recommendation="Ensure sudo() usage is justified and secure"
            ))
        
        return issues
    
    def _check_data_validation(self, file_path: str, content: str, tree: ast.AST) -> List[SecurityIssue]:
        """Check for missing data validation"""
        issues = []
        
        # Look for user input handling without validation
        input_patterns = [
            r'request\.params\.get\(',
            r'self\.env\.context\.get\(',
            r'vals\.get\(',
        ]
        
        for pattern in input_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Check if there's validation nearby
                line_num = content[:match.start()].count('\n') + 1
                surrounding_lines = content.split('\n')[max(0, line_num-3):line_num+3]
                
                validation_keywords = ['validate', 'check', 'assert', 'raise', 'if not']
                has_validation = any(keyword in ' '.join(surrounding_lines) for keyword in validation_keywords)
                
                if not has_validation:
                    issues.append(SecurityIssue(
                        issue_id="MISSING_VALIDATION",
                        severity=VulnerabilityLevel.MEDIUM,
                        title="Missing Input Validation",
                        description="User input handling without apparent validation",
                        file_path=file_path,
                        line_number=line_num,
                        recommendation="Add proper input validation and sanitization"
                    ))
        
        return issues
    
    def _check_xml_injection(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Check for XML injection vulnerabilities"""
        issues = []
        
        # Look for dynamic XML content
        if re.search(r'<.*%\([^)]+\).*>', content):
            issues.append(SecurityIssue(
                issue_id="XML_INJECTION",
                severity=VulnerabilityLevel.HIGH,
                title="Potential XML Injection",
                description="Dynamic content in XML without proper escaping",
                file_path=file_path,
                recommendation="Use proper XML escaping for dynamic content",
                cwe_id="CWE-91"
            ))
        
        return issues
    
    def _check_access_rights_xml(self, file_path: str, root: ET.Element) -> List[SecurityIssue]:
        """Check access rights in XML files"""
        issues = []
        
        # Look for overly permissive groups
        for record in root.findall(".//record[@model='ir.ui.view']"):
            groups_field = record.find(".//field[@name='groups_id']")
            if groups_field is None:
                issues.append(SecurityIssue(
                    issue_id="NO_VIEW_GROUPS",
                    severity=VulnerabilityLevel.LOW,
                    title="View Without Group Restrictions",
                    description="View has no group restrictions",
                    file_path=file_path,
                    recommendation="Consider adding appropriate group restrictions"
                ))
        
        return issues
    
    def _check_domain_security(self, file_path: str, root: ET.Element) -> List[SecurityIssue]:
        """Check domain security in XML"""
        issues = []
        
        # Look for potentially unsafe domains
        for field in root.findall(".//field[@name='domain']"):
            domain_text = field.text or ""
            
            # Check for user-controlled domain without proper validation
            if "uid" in domain_text and "user" not in domain_text:
                issues.append(SecurityIssue(
                    issue_id="UNSAFE_DOMAIN",
                    severity=VulnerabilityLevel.MEDIUM,
                    title="Potentially Unsafe Domain",
                    description="Domain references uid without user context validation",
                    file_path=file_path,
                    recommendation="Ensure domain properly validates user context"
                ))
        
        return issues
    
    def _check_access_rights_csv(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Check access rights in CSV files"""
        issues = []
        
        lines = content.strip().split('\n')
        if len(lines) < 2:  # No data rows
            return issues
        
        for i, line in enumerate(lines[1:], 2):  # Skip header
            parts = line.split(',')
            if len(parts) >= 8:
                # Check if all permissions are granted (1,1,1,1)
                perms = parts[-4:]
                if all(p.strip() == '1' for p in perms):
                    issues.append(SecurityIssue(
                        issue_id="OVERLY_PERMISSIVE",
                        severity=VulnerabilityLevel.MEDIUM,
                        title="Overly Permissive Access Rights",
                        description=f"Full permissions granted on line {i}",
                        file_path=file_path,
                        line_number=i,
                        recommendation="Review and restrict permissions as needed"
                    ))
        
        return issues
    
    def _check_compliance(self, module_spec: ModuleSpec, 
                         generated_files: Dict[str, str],
                         framework: ComplianceFramework) -> List[ComplianceIssue]:
        """Check compliance with specific framework"""
        issues = []
        
        if framework == ComplianceFramework.GDPR:
            issues.extend(self._check_gdpr_compliance(module_spec, generated_files))
        elif framework == ComplianceFramework.HIPAA:
            issues.extend(self._check_hipaa_compliance(module_spec, generated_files))
        
        return issues
    
    def _check_gdpr_compliance(self, module_spec: ModuleSpec, 
                             generated_files: Dict[str, str]) -> List[ComplianceIssue]:
        """Check GDPR compliance"""
        issues = []
        
        # Check for personal data fields without proper handling
        personal_data_fields = [
            'email', 'phone', 'mobile', 'address', 'name', 'firstname', 
            'lastname', 'birthdate', 'social_security', 'passport'
        ]
        
        for model in module_spec.models:
            has_personal_data = False
            
            for field in model.fields:
                if any(pd_field in field.name.lower() for pd_field in personal_data_fields):
                    has_personal_data = True
                    break
            
            if has_personal_data:
                # Check for data retention policy
                issues.append(ComplianceIssue(
                    issue_id="GDPR_DATA_RETENTION",
                    framework=ComplianceFramework.GDPR,
                    requirement="Data Retention Policy",
                    description=f"Model {model.name} handles personal data but lacks retention policy",
                    file_path="models/" + model.name.split('.')[-1] + ".py",
                    recommendation="Implement data retention and deletion mechanisms",
                    mandatory=True
                ))
                
                # Check for consent tracking
                consent_field = any(f.name in ['consent', 'privacy_consent', 'gdpr_consent'] 
                                  for f in model.fields)
                if not consent_field:
                    issues.append(ComplianceIssue(
                        issue_id="GDPR_CONSENT",
                        framework=ComplianceFramework.GDPR,
                        requirement="Consent Tracking",
                        description=f"Model {model.name} handles personal data but lacks consent tracking",
                        file_path="models/" + model.name.split('.')[-1] + ".py",
                        recommendation="Add consent tracking fields and mechanisms",
                        mandatory=False
                    ))
        
        return issues
    
    def _check_hipaa_compliance(self, module_spec: ModuleSpec, 
                              generated_files: Dict[str, str]) -> List[ComplianceIssue]:
        """Check HIPAA compliance"""
        issues = []
        
        # Check for health information fields
        health_fields = [
            'medical', 'health', 'diagnosis', 'treatment', 'patient',
            'doctor', 'physician', 'medication', 'prescription'
        ]
        
        for model in module_spec.models:
            model_text = f"{model.name} {model.description}".lower()
            field_text = " ".join([f.name for f in model.fields]).lower()
            
            if any(h_field in f"{model_text} {field_text}" for h_field in health_fields):
                issues.append(ComplianceIssue(
                    issue_id="HIPAA_ENCRYPTION",
                    framework=ComplianceFramework.HIPAA,
                    requirement="Data Encryption",
                    description=f"Model {model.name} handles health information but lacks encryption",
                    file_path="models/" + model.name.split('.')[-1] + ".py",
                    recommendation="Implement field-level encryption for sensitive health data",
                    mandatory=True
                ))
        
        return issues
    
    def _calculate_security_score(self, security_issues: List[SecurityIssue], 
                                compliance_issues: List[ComplianceIssue]) -> float:
        """Calculate overall security score (0-100)"""
        base_score = 100.0
        
        # Deduct points based on severity
        severity_penalties = {
            VulnerabilityLevel.LOW: 2,
            VulnerabilityLevel.MEDIUM: 5,
            VulnerabilityLevel.HIGH: 15,
            VulnerabilityLevel.CRITICAL: 30
        }
        
        for issue in security_issues:
            base_score -= severity_penalties.get(issue.severity, 5)
        
        # Deduct points for compliance issues
        for issue in compliance_issues:
            penalty = 20 if issue.mandatory else 5
            base_score -= penalty
        
        return max(0.0, base_score)
    
    def generate_security_report(self, scan_result: SecurityScanResult) -> str:
        """Generate human-readable security report"""
        report = []
        report.append(f"Security Analysis Report for {scan_result.module_name}")
        report.append("=" * 50)
        report.append(f"Scan Date: {scan_result.scan_timestamp}")
        report.append(f"Overall Score: {scan_result.overall_score:.1f}/100")
        report.append(f"Status: {'PASSED' if scan_result.passed else 'FAILED'}")
        report.append("")
        
        if scan_result.security_issues:
            report.append("Security Issues:")
            report.append("-" * 20)
            
            for issue in sorted(scan_result.security_issues, 
                              key=lambda x: list(VulnerabilityLevel).index(x.severity), 
                              reverse=True):
                report.append(f"[{issue.severity.value.upper()}] {issue.title}")
                report.append(f"  File: {issue.file_path}")
                if issue.line_number:
                    report.append(f"  Line: {issue.line_number}")
                report.append(f"  Description: {issue.description}")
                report.append(f"  Recommendation: {issue.recommendation}")
                if issue.cwe_id:
                    report.append(f"  CWE: {issue.cwe_id}")
                report.append("")
        
        if scan_result.compliance_issues:
            report.append("Compliance Issues:")
            report.append("-" * 20)
            
            for issue in scan_result.compliance_issues:
                mandatory_str = " (MANDATORY)" if issue.mandatory else ""
                report.append(f"[{issue.framework.value.upper()}] {issue.requirement}{mandatory_str}")
                report.append(f"  File: {issue.file_path}")
                report.append(f"  Description: {issue.description}")
                report.append(f"  Recommendation: {issue.recommendation}")
                report.append("")
        
        return "\n".join(report)
    
    def _load_security_rules(self) -> Dict[str, Any]:
        """Load security scanning rules"""
        # In a real implementation, this would load from external configuration
        return {
            "sql_injection_patterns": [
                r'cr\.execute\s*\(\s*["\'].*%s.*["\']',
                r'self\._cr\.execute\s*\(\s*.*\+.*\)'
            ],
            "secret_patterns": [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']'
            ]
        }
    
    def _load_compliance_rules(self) -> Dict[str, Any]:
        """Load compliance checking rules"""
        return {
            "gdpr": {
                "personal_data_fields": [
                    "email", "phone", "address", "name", "birthdate"
                ],
                "required_fields": ["consent", "data_retention_date"]
            },
            "hipaa": {
                "health_fields": [
                    "medical", "health", "diagnosis", "patient"
                ],
                "required_encryption": True
            }
        }