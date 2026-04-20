#!/usr/bin/env python3
"""
YALI AI OS - Security Audit Script
Scans the repository for potential security issues and sensitive data.
"""

import os
import re
import sys
from pathlib import Path

class SecurityAuditor:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.issues = []

    def audit(self):
        """Run complete security audit"""
        print("🔒 YALI Security Audit Starting...")
        print("=" * 50)

        self.check_gitignore()
        self.scan_sensitive_patterns()
        self.check_forbidden_files()
        self.check_committed_secrets()

        print("=" * 50)
        if self.issues:
            print(f"❌ Found {len(self.issues)} security issues:")
            for issue in self.issues:
                print(f"  - {issue}")
            print("\n🚨 SECURITY VIOLATIONS DETECTED!")
            print("Please fix these issues before committing.")
            return False
        else:
            print("✅ Security audit passed - no issues found")
            return True

    def check_gitignore(self):
        """Check if .gitignore exists and contains security patterns"""
        gitignore_path = self.repo_path / '.gitignore'
        if not gitignore_path.exists():
            self.issues.append("Missing .gitignore file")
            return

        with open(gitignore_path, 'r') as f:
            content = f.read().lower()

        required_patterns = ['.env', 'secret', 'key', 'password', 'token']
        for pattern in required_patterns:
            if pattern not in content:
                self.issues.append(f".gitignore missing pattern: {pattern}")

    def scan_sensitive_patterns(self):
        """Scan all files for sensitive patterns"""
        sensitive_patterns = [
            r'password\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'secret\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'api_key\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'access_token\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'client_secret\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'aws_access_key_id\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'aws_secret_access_key\s*[:=]\s*[\'"][^\'"]+[\'"]',
        ]

        for file_path in self.repo_path.rglob('*'):
            if (file_path.is_file() and
                not file_path.name.startswith('.') and
                file_path.suffix not in ['.pyc', '.pyo'] and
                '.git' not in str(file_path)):

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    for pattern in sensitive_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            self.issues.append(f"Sensitive data pattern in {file_path}: {pattern}")
                except:
                    pass  # Skip binary files

    def check_forbidden_files(self):
        """Check for forbidden file types"""
        forbidden_extensions = ['.key', '.pem', '.p12', '.pfx', '.env']
        forbidden_names = ['secrets', 'credentials', 'passwords']

        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file():
                # Check extensions
                if file_path.suffix in forbidden_extensions:
                    self.issues.append(f"Forbidden file type: {file_path}")

                # Check names
                if any(name in file_path.name.lower() for name in forbidden_names):
                    self.issues.append(f"Forbidden file name: {file_path}")

    def check_committed_secrets(self):
        """Check if any sensitive files are already committed"""
        try:
            import subprocess
            result = subprocess.run(['git', 'ls-files'], cwd=self.repo_path,
                                  capture_output=True, text=True)

            if result.returncode == 0:
                committed_files = result.stdout.splitlines()
                forbidden_patterns = ['.env', 'secret', 'key', 'password']

                for file in committed_files:
                    if any(pattern in file.lower() for pattern in forbidden_patterns):
                        self.issues.append(f"Potentially sensitive file committed: {file}")
        except:
            pass  # Git not available or not a git repo

def main():
    repo_path = Path(__file__).parent
    auditor = SecurityAuditor(repo_path)
    success = auditor.audit()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()