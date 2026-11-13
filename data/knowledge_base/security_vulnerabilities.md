# Python Security Vulnerabilities, CWE & OWASP Guidelines

## Critical Injection Vulnerabilities
### 1. Code Injection via `eval()` and `exec()` (CWE-95)
- **Problem**: Executing arbitrary untrusted user input using `eval()`, `exec()`, or `compile()` allows remote code execution (RCE).
- **Remediation**:
  - Never run `eval()` on unsanitized strings.
  - If mathematical formula evaluation is needed, use `ast.literal_eval()` for literal data structures, or specialized arithmetic parser libraries (e.g., `sympy` or simple token-based parsers).

### 2. Command Injection via `os.system` / `subprocess` (CWE-78)
- **Problem**: Passing unescaped strings to `os.system()`, `os.popen()`, or `subprocess.Popen(..., shell=True)` permits shell command chaining (`command; rm -rf /`).
- **Remediation**:
  - Always set `shell=False` in `subprocess.run()` or `subprocess.Popen()`.
  - Pass arguments as a discrete list of tokens: `subprocess.run(["ls", "-l", target_path], shell=False, check=True)`.
  - Sanitize and validate file paths using `os.path.abspath()` and prevent path traversal (`../`).

### 3. SQL Injection (CWE-89)
- **Problem**: Constructing SQL queries using string formatting or f-strings: `f"SELECT * FROM users WHERE email='{email}'"`.
- **Remediation**:
  - Always use parameterized queries or ORM bindings (e.g., `cursor.execute("SELECT * FROM users WHERE email = %s", (email,))`).

## Insecure Deserialization (CWE-502)
### `pickle` & `yaml.load()`
- **Problem**: Python's `pickle.loads()` can execute arbitrary bytecode during deserialization if an attacker tampers with the payload (`__reduce__` hook).
- **Remediation**:
  - Never unpickle untrusted data. Use safer serialization standards such as JSON (`json.loads()`), Protocol Buffers, or MessagePack.
  - In PyYAML, always use `yaml.safe_load(data)` instead of `yaml.load(data, Loader=yaml.Loader)`.

## Resource Exhaustion & Denial of Service (CWE-400)
### 1. Regular Expression Denial of Service (ReDoS) (CWE-1333)
- **Problem**: Catastrophic backtracking in regex patterns with overlapping nested quantifiers (e.g., `(a+)+$`).
- **Remediation**: Use linear-time regex engines (like Google's `re2`), simplify expressions, or enforce strict input length limits before pattern matching.

### 2. Unbounded Memory Allocation & Infinite Recursion
- **Problem**: Loading entire gigabyte files into memory via `file.read()`, or unbounded recursion exceeding `sys.getrecursionlimit()`.
- **Remediation**: Stream large files in chunks (`for chunk in iter(lambda: f.read(4096), b""):`) and enforce recursion depth base cases or rewrite to iterative loops.

## Cryptography & Secrets Management
- **Avoid Weak Hash Functions**: Do not use `hashlib.md5()` or `hashlib.sha1()` for password hashing or security integrity. Use `hashlib.sha256` for digests, and `argon2`, `bcrypt`, or `scrypt` for password hashing.
- **Never Hardcode Secrets**: Store API keys, tokens, and passwords in environment variables (`os.getenv()`) and load them with `dotenv`.

