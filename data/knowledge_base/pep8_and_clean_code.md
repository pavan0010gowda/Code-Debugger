# Python Style & Clean Code Guidelines (PEP 8 & Industry Best Practices)

## Naming Conventions
- **Variables and Functions**: Use `snake_case` (e.g., `calculate_tax`, `user_count`).
- **Classes**: Use `PascalCase` / `CapWords` (e.g., `InvoiceManager`, `HttpClient`).
- **Constants**: Use `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT_SEC`).
- **Protected/Private Attributes**: Use single leading underscore `_helper_method()` for internal methods, double leading underscore `__mangled_var` only when necessary to avoid naming clashes in subclasses.
- **Avoid Ambiguous Names**: Never use single characters `l` (lowercase L), `O` (uppercase O), or `I` (uppercase I) as isolated variable names.

## Formatting & Layout
- **Indentation**: 4 spaces per indentation level. Never mix tabs and spaces.
- **Maximum Line Length**: Limit lines to 79-88 characters. For long expressions, use parentheses for line continuation rather than backslashes.
- **Blank Lines**:
  - Surround top-level function and class definitions with 2 blank lines.
  - Method definitions inside a class are surrounded by a single blank line.
  - Use blank lines sparingly inside functions to separate logical sections.
- **Imports**:
  - Always put imports at the top of the file, after any module comments/docstrings.
  - Group imports in the following order, separated by a blank line:
    1. Standard library imports (e.g., `os`, `sys`, `math`, `typing`).
    2. Related third-party imports (e.g., `pydantic`, `langchain`, `fastapi`).
    3. Local application/library specific imports.
  - Avoid wildcard imports `from module import *` because it pollutes the namespace and hides undefined names.

## Typing & Documentation
- **Type Annotations**: Always provide type hints for function arguments and return types:
  ```python
  def find_user_by_id(user_id: int, include_deleted: bool = False) -> Optional[User]:
      ...
  ```
- **Docstrings (PEP 257)**:
  - Write docstrings for all public modules, functions, classes, and methods.
  - Use Google style or Sphinx style docstrings describing: Summary, Args, Returns, Raises, and Examples.

## Idiomatic Python Patterns (Zen of Python)
- **EAFP over LBYL**: "Easier to ask for forgiveness than permission". Prefer `try...except KeyError` over multiple nested checks when accessing dictionaries, provided the exception is tightly scoped.
- **Context Managers (`with` statement)**: Always use `with open(...) as f:` for file operations, locks, and network sockets to ensure deterministic cleanup.
- **List Comprehensions & Generators**: Use comprehensions for simple transformations. If the collection is massive, use generator expressions `(x for x in iterable)` to minimize memory footprints.
- **Avoid Anti-patterns**:
  - Never compare to singletons like `None` using `==`. Always use `if var is None:` or `if var is not None:`.
  - Avoid boolean comparisons like `if condition == True:`. Simply use `if condition:`.

