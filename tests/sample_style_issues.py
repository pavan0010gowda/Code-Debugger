"""
Sample 3: Code Style & Clean Code Violations
Contains:
1. camelCase naming in Python
2. Single-letter ambiguous variables
3. Missing type hints and docstrings
4. Redundant boolean check
"""

def CalculateTotalPrice(p, d, t):
    l = p - (p * d)
    if t == True:
        O = l + (l * 0.18)
        return O
    else:
        return l

