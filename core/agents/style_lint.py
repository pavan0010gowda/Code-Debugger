from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq


STYLE_LINT_SYSTEM_PROMPT = """You are the Style/Lint Agent in an automated code review squad.
Your mission is to enforce clean code and PEP 8 standards with brief, actionable feedback.

### PROMPT ENGINEERING TECHNIQUE: Few-Shot Prompting
Review code learning from this standard example:
- Bad: `def CalculateTotalPrice(p, d, t):` -> Single-letter vars, camelCase in Python, missing docstring.
- Clean: `def calculate_total_price(price: float, discount: float) -> float:` -> snake_case, descriptive names.

### Output Format (Keep it short & punchy):
1. **Style Health Score**: Score out of 100 with a 1-sentence assessment.
2. **Key Style Improvements (Bullet Points)**:
   - **Naming**: snake_case vs camelCase, descriptive variable names.
   - **Formatting & PEP 8**: Spacing, line lengths, unused elements.
   - **Type Hints & Cleanliness**: Simple type annotations where helpful.

Keep it simple, short, and practical without academic filler.
"""

STYLE_LINT_USER_PROMPT = """Analyze this code for style and PEP 8 clean code hygiene.

### Code:
```{language}
{code}
```

### Style Context:
{rag_context}

Provide a concise style scorecard and key recommendations:"""


class StyleLintAgent:
    """
    Style/Lint Agent: Enforces readability, naming conventions, docstrings,
    and PEP 8 standards using Few-Shot prompting.
    """

    PROMPT_TECHNIQUE = "Few-Shot Prompting (Exemplar-Driven)"

    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", STYLE_LINT_SYSTEM_PROMPT),
            ("user", STYLE_LINT_USER_PROMPT)
        ])
        # LCEL Chain: Prompt | Model | Parser
        self.chain = self.prompt_template | self.llm | StrOutputParser()

    def analyze(self, code: str, language: str = "python", rag_context: str = "") -> str:
        """Execute the style lint chain."""
        return self.chain.invoke({
            "code": code,
            "language": language,
            "rag_context": rag_context if rag_context.strip() else "Standard PEP 8 specifications apply."
        })

    def get_prompt_metadata(self) -> Dict[str, str]:
        """Returns prompt telemetry for transparent evaluation."""
        return {
            "agent": "Style/Lint Agent",
            "technique": self.PROMPT_TECHNIQUE,
            "system_prompt": STYLE_LINT_SYSTEM_PROMPT,
            "user_prompt_template": STYLE_LINT_USER_PROMPT
        }
