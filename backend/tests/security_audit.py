#!/usr/bin/env python3
"""
Security Audit Script for ORGON B2B Platform
Checks for OWASP Top 10 vulnerabilities and security best practices
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any
import ast


class SecurityAuditor:
    """Security audit tool for Python code."""
    
    def __init__(self, root_dir: str = "backend"):
        self.root_dir = Path(root_dir)
        self.issues = []
        self.stats = {
            "files_scanned": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
    
    def add_issue(self, severity: str, category: str, file: Path, line: int, description: str, code: str = None):
        """Add security issue to list."""
        self.issues.append({
            "severity": severity,
            "category": category,
            "file": str(file),
            "line": line,
            "description": description,
            "code": code
        })
        self.stats[severity] += 1
    
    def scan_file(self, file_path: Path):
        """Scan a single Python file for security issues."""
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Check for common security issues
            self.check_sql_injection(file_path, content, lines)
            self.check_hardcoded_secrets(file_path, content, lines)
            self.check_command_injection(file_path, content, lines)
            self.check_insecure_deserialization(file_path, content, lines)
            self.check_weak_crypto(file_path, content, lines)
            self.check_debug_enabled(file_path, content, lines)
            self.check_sensitive_data_exposure(file_path, content, lines)
            
            self.stats["files_scanned"] += 1
            
        except Exception as e:
            print(f"⚠️  Error scanning {file_path}: {e}")
    
    def check_sql_injection(self, file_path: Path, content: str, lines: List[str]):
        """Check for SQL injection vulnerabilities."""
        # Pattern: String formatting in SQL queries
        patterns = [
            (r'f["\'].*SELECT.*{.*}.*["\']', 'critical', 'SQL query with f-string interpolation'),
            (r'["\'].*SELECT.*%s.*["\'].format\(', 'critical', 'SQL query with .format()'),
            (r'["\'].*SELECT.*\+.*["\']', 'high', 'SQL query with string concatenation'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, severity, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.add_issue(
                        severity=severity,
                        category="SQL Injection",
                        file=file_path,
                        line=i,
                        description=desc,
                        code=line.strip()
                    )
    
    def check_hardcoded_secrets(self, file_path: Path, content: str, lines: List[str]):
        """Check for hardcoded secrets (API keys, passwords, tokens)."""
        patterns = [
            (r'(?:api_key|apikey|api-key)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', 'critical', 'Hardcoded API key'),
            (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{1,}["\']', 'critical', 'Hardcoded password'),
            (r'(?:secret|token|auth)\s*=\s*["\'][a-zA-Z0-9+/=]{20,}["\']', 'high', 'Hardcoded secret/token'),
            (r'[a-zA-Z0-9]{32,}', 'low', 'Potential hardcoded secret (long string)'),
        ]
        
        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            if line.strip().startswith('#') or line.strip().startswith('"""') or line.strip().startswith("'''"):
                continue
            
            for pattern, severity, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.add_issue(
                        severity=severity,
                        category="Hardcoded Secrets",
                        file=file_path,
                        line=i,
                        description=desc,
                        code=line.strip()
                    )
    
    def check_command_injection(self, file_path: Path, content: str, lines: List[str]):
        """Check for command injection vulnerabilities."""
        patterns = [
            (r'os\.system\(.*\+.*\)', 'critical', 'os.system() with string concatenation'),
            (r'subprocess\..*shell=True', 'high', 'subprocess with shell=True'),
            (r'eval\(', 'critical', 'Use of eval()'),
            (r'exec\(', 'critical', 'Use of exec()'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, severity, desc in patterns:
                if re.search(pattern, line):
                    self.add_issue(
                        severity=severity,
                        category="Command Injection",
                        file=file_path,
                        line=i,
                        description=desc,
                        code=line.strip()
                    )
    
    def check_insecure_deserialization(self, file_path: Path, content: str, lines: List[str]):
        """Check for insecure deserialization."""
        patterns = [
            (r'pickle\.loads?\(', 'high', 'Use of pickle (insecure deserialization)'),
            (r'yaml\.load\((?!.*Loader)', 'high', 'yaml.load() without safe Loader'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, severity, desc in patterns:
                if re.search(pattern, line):
                    self.add_issue(
                        severity=severity,
                        category="Insecure Deserialization",
                        file=file_path,
                        line=i,
                        description=desc,
                        code=line.strip()
                    )
    
    def check_weak_crypto(self, file_path: Path, content: str, lines: List[str]):
        """Check for weak cryptographic practices."""
        patterns = [
            (r'hashlib\.(md5|sha1)\(', 'medium', 'Weak hash algorithm (MD5/SHA1)'),
            (r'random\.random\(', 'medium', 'Use of random.random() instead of secrets module'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, severity, desc in patterns:
                if re.search(pattern, line):
                    self.add_issue(
                        severity=severity,
                        category="Weak Cryptography",
                        file=file_path,
                        line=i,
                        description=desc,
                        code=line.strip()
                    )
    
    def check_debug_enabled(self, file_path: Path, content: str, lines: List[str]):
        """Check for debug mode enabled in production."""
        patterns = [
            (r'DEBUG\s*=\s*True', 'high', 'DEBUG mode enabled'),
            (r'app\.debug\s*=\s*True', 'high', 'Flask/FastAPI debug mode enabled'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, severity, desc in patterns:
                if re.search(pattern, line):
                    self.add_issue(
                        severity=severity,
                        category="Debug Mode",
                        file=file_path,
                        line=i,
                        description=desc,
                        code=line.strip()
                    )
    
    def check_sensitive_data_exposure(self, file_path: Path, content: str, lines: List[str]):
        """Check for sensitive data in logs."""
        patterns = [
            (r'log.*\(.*password.*\)', 'high', 'Password logged'),
            (r'log.*\(.*api_key.*\)', 'high', 'API key logged'),
            (r'log.*\(.*secret.*\)', 'high', 'Secret logged'),
            (r'print\(.*password.*\)', 'medium', 'Password printed to console'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, severity, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.add_issue(
                        severity=severity,
                        category="Sensitive Data Exposure",
                        file=file_path,
                        line=i,
                        description=desc,
                        code=line.strip()
                    )
    
    def scan_directory(self):
        """Scan all Python files in directory."""
        print(f"🔍 Scanning {self.root_dir} for security issues...\n")
        
        python_files = list(self.root_dir.rglob("*.py"))
        
        for file_path in python_files:
            # Skip test files and migrations
            if "test" in str(file_path) and file_path.name != "security_audit.py":
                continue
            if "migration" in str(file_path):
                continue
            
            self.scan_file(file_path)
        
        return self.issues
    
    def print_report(self):
        """Print security audit report."""
        print(f"\n{'='*80}")
        print(f"{'SECURITY AUDIT REPORT':^80}")
        print(f"{'='*80}\n")
        
        print(f"📊 Files scanned: {self.stats['files_scanned']}")
        print(f"🚨 Total issues: {len(self.issues)}\n")
        
        print(f"Severity Breakdown:")
        print(f"  🔴 Critical: {self.stats['critical']}")
        print(f"  🟠 High:     {self.stats['high']}")
        print(f"  🟡 Medium:   {self.stats['medium']}")
        print(f"  🟢 Low:      {self.stats['low']}")
        print(f"  ℹ️  Info:     {self.stats['info']}")
        
        if self.issues:
            print(f"\n{'='*80}")
            print("DETAILED FINDINGS")
            print(f"{'='*80}\n")
            
            # Group by severity
            by_severity = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
            for issue in self.issues:
                by_severity[issue["severity"]].append(issue)
            
            for severity in ["critical", "high", "medium", "low", "info"]:
                if by_severity[severity]:
                    icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}[severity]
                    print(f"\n{icon} {severity.upper()} SEVERITY\n")
                    
                    for issue in by_severity[severity]:
                        print(f"  [{issue['category']}] {issue['file']}:{issue['line']}")
                        print(f"  {issue['description']}")
                        if issue['code']:
                            print(f"  Code: {issue['code'][:100]}")
                        print()
        
        print(f"\n{'='*80}")
        print("RECOMMENDATIONS")
        print(f"{'='*80}\n")
        
        if self.stats['critical'] > 0:
            print("🔴 CRITICAL: Fix immediately before production deployment!")
        if self.stats['high'] > 0:
            print("🟠 HIGH: Address these issues as soon as possible.")
        if self.stats['medium'] > 0:
            print("🟡 MEDIUM: Plan to fix in next sprint.")
        if self.stats['low'] > 0:
            print("🟢 LOW: Consider fixing when refactoring.")
        
        if len(self.issues) == 0:
            print("✅ No security issues found!")
        
        print()
        
        # Return exit code
        if self.stats['critical'] > 0:
            return 2  # Critical issues
        elif self.stats['high'] > 0:
            return 1  # High issues
        else:
            return 0  # No critical/high issues


def main():
    """Run security audit."""
    auditor = SecurityAuditor(root_dir="backend")
    auditor.scan_directory()
    exit_code = auditor.print_report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
