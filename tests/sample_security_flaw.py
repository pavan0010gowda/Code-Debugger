"""
Sample 2: Security Vulnerabilities & Dangerous Sinks
Contains:
1. CWE-95: Untrusted string evaluation with eval()
2. CWE-22: Path traversal vulnerability in file reading
3. Plaintext secret hardcoded
"""

import os

API_SECRET_TOKEN = "sk_live_998877665544332211"  # VULNERABILITY: Hardcoded secret

def calculate_formula(user_expression):
    # VULNERABILITY: Arbitrary Code Execution (RCE)
    result = eval(user_expression)
    return result

def retrieve_user_log(filename):
    # VULNERABILITY: Path Traversal (e.g. filename = "../../../etc/passwd")
    filepath = f"/var/logs/{filename}"
    with open(filepath, "r") as f:
        return f.read()

