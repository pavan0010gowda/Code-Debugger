import re
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq


FIXER_SYSTEM_PROMPT = """You are the Fixer Agent in an automated code review squad.
Your objective is to rewrite the code with minimal, elegant, and pythonic fixes while preserving original intent.

### Guiding Principles:
1. **Minimal & Clean Fixes**:
   - Fix all confirmed syntax and runtime errors directly (e.g. use f-strings `f"Final Total: {{final_total}}"` to fix TypeError).
   - Use simple, idiomatic Python (e.g., `sum(prices)`, `max(total - discount, 0)`).
   - Do NOT add unnecessary enterprise boilerplate, heavy logging, or complex generic wrappers.
2. **Preserve Original Structure & Interface**:
   - Keep the original function names and parameters.
   - If a caller script or sample input exists at the bottom, wrap it inside `if __name__ == "__main__":`.
3. **Explicit Edge Case Handling**:
   - Handle empty inputs (e.g., empty collection yields 0).
   - Handle boundary values (e.g., discount greater than total clamped to 0 using `max(...)`).

### Output Structure:
1. **Summary of Fixes**: 2-4 bullet points describing changes (marked `[FIXED]`).
2. **🛡️ Edge Cases Handled**:
   - Normal case: e.g. `[100, 200, 300]` with discount `10` -> `590`.
   - Empty input: `[]` -> `0`.
   - Discount > total: clamped safely to `0`.
   - Zero discount: functions as expected.
3. **Refactored Code Block**:
```python
# Clean, minimal, bug-free Python code
```
"""

FIXER_USER_PROMPT = """Refactor this code to fix all confirmed defects simply and elegantly.

### Original Code:
```python
{code}
```

### Bug Report:
{bug_report}

### Style Feedback:
{style_report}

### Technical Guidelines:
{rag_context}

Provide the summary of fixes, edge cases handled, and the clean refactored code:"""


FIXER_REFLECTION_SYSTEM_PROMPT = """You are the Fixer Agent executing a REFLECTION & SELF-CORRECTION loop.
The previous version of your refactored code failed tests inside the execution sandbox.

### PROMPT ENGINEERING TECHNIQUE: Reflection & Iterative Self-Correction (ReAct)
1. Review the sandbox execution error traceback.
2. Identify why the test failed.
3. Provide the corrected, clean Python code in a ```python ... ``` block.
"""

FIXER_REFLECTION_USER_PROMPT = """The code failed in the sandbox execution!

### Current Code:
```python
{current_code}
```

### Test Suite:
```python
{test_code}
```

### Sandbox Error Output:
{sandbox_error}

Reflect on this failure and output the corrected code:"""


class FixerAgent:
    """
    Fixer Agent: Generates minimal, elegant, bug-free refactored code
    and self-heals via reflection if sandbox verification fails.
    """

    PROMPT_TECHNIQUE = "Reflection & Self-Correction (ReAct)"

    def __init__(self, llm: ChatGroq):
        self.llm = llm
        
        # Standard Refactoring Chain
        self.refactor_prompt = ChatPromptTemplate.from_messages([
            ("system", FIXER_SYSTEM_PROMPT),
            ("user", FIXER_USER_PROMPT)
        ])
        self.refactor_chain = self.refactor_prompt | self.llm | StrOutputParser()

        # Reflection / Self-Healing Chain
        self.reflection_prompt = ChatPromptTemplate.from_messages([
            ("system", FIXER_REFLECTION_SYSTEM_PROMPT),
            ("user", FIXER_REFLECTION_USER_PROMPT)
        ])
        self.reflection_chain = self.reflection_prompt | self.llm | StrOutputParser()

    def refactor(self, code: str, bug_report: str, style_report: str, rag_context: str = "") -> str:
        """Run initial refactoring based on squad reports."""
        return self.refactor_chain.invoke({
            "code": code,
            "bug_report": bug_report,
            "style_report": style_report,
            "rag_context": rag_context if rag_context.strip() else "Standard Python clean code conventions."
        })

    def reflect_and_correct(self, current_code: str, test_code: str, sandbox_error: str) -> str:
        """Execute the self-correction reflection step with sandbox feedback."""
        return self.reflection_chain.invoke({
            "current_code": current_code,
            "test_code": test_code,
            "sandbox_error": sandbox_error
        })

    @staticmethod
    def extract_python_code(response_text: str) -> str:
        """Extract pure Python code block from LLM markdown response."""
        code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", response_text, re.DOTALL)
        if code_blocks:
            # Return the largest code block (the actual refactored script)
            return max(code_blocks, key=len).strip()
        return response_text.strip()

    def get_prompt_metadata(self) -> Dict[str, str]:
        """Returns prompt telemetry for transparent evaluation."""
        return {
            "agent": "Fixer Agent",
            "technique": self.PROMPT_TECHNIQUE,
            "system_prompt": FIXER_SYSTEM_PROMPT,
            "reflection_system_prompt": FIXER_REFLECTION_SYSTEM_PROMPT
        }
