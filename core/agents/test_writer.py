import re
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq


TEST_WRITER_SYSTEM_PROMPT = """You are the Test-Writer Agent in an automated code review squad.
Your mission is to write clean, deterministic unit tests that verify the refactored code across both normal and edge-case inputs.

### Test Coverage Requirements:
1. **Happy Path / Normal Input**: Test standard valid inputs and assert the exact expected calculation result.
2. **Empty Input**: Test empty collections (e.g., `[]` or `""`) and verify safe return values.
3. **Boundary Values**: Test boundary values (e.g., discount greater than total, zero values, single element).
4. **Default Parameters**: Test calling the function with default arguments.

### Execution Guidelines:
- Assume the refactored code will be present in the execution scope.
- Use clean standard `assert` statements with helpful error messages:
  ```python
  assert calculate_total([100, 200, 300], 10) == 590, "Expected 590 for normal input"
  ```
- Wrap assertions in a clean test runner function that prints descriptive progress:
  ```python
  print("✓ Test 1: Normal input passed")
  print("✓ Test 2: Empty input passed")
  print("✓ Test 3: Boundary value passed")
  print("All tests passed successfully! [VERIFIED]")
  ```
- Respond strictly with executable Python test code inside a single ```python ... ``` block.
"""

TEST_WRITER_USER_PROMPT = """Generate an automated test suite verifying the correctness of this refactored code.

### Code under Test:
```python
{code}
```

### Bugs and Edge Cases to Verify:
{bug_context}

Provide the executable Python test suite:"""


class TestWriterAgent:
    """
    Test-Writer Agent: Generates comprehensive test suites using automated assertions
    and edge-case fuzzing to execute in the isolated sandbox.
    """

    PROMPT_TECHNIQUE = "Test-Driven Specification & Assertion Prompting"

    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", TEST_WRITER_SYSTEM_PROMPT),
            ("user", TEST_WRITER_USER_PROMPT)
        ])
        # LCEL Chain: Prompt | Model | Parser
        self.chain = self.prompt_template | self.llm | StrOutputParser()

    def generate_tests(self, code: str, bug_context: str = "") -> str:
        """Generate Python test suite."""
        return self.chain.invoke({
            "code": code,
            "bug_context": bug_context if bug_context.strip() else "Verify all public functions and edge cases."
        })

    @staticmethod
    def extract_python_tests(response_text: str) -> str:
        """Extract clean test code from markdown response."""
        code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", response_text, re.DOTALL)
        if code_blocks:
            return max(code_blocks, key=len).strip()
        return response_text.strip()

    def get_prompt_metadata(self) -> Dict[str, str]:
        """Returns prompt telemetry for transparent evaluation."""
        return {
            "agent": "Test-Writer Agent",
            "technique": self.PROMPT_TECHNIQUE,
            "system_prompt": TEST_WRITER_SYSTEM_PROMPT,
            "user_prompt_template": TEST_WRITER_USER_PROMPT
        }
