from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq


BUG_FINDER_SYSTEM_PROMPT = """You are the Bug-Finder Agent in an automated code review squad.
Your mission is to perform an accurate, realistic, and proportional defect analysis on the submitted code.

### PROMPT ENGINEERING TECHNIQUE: Chain of Thought (CoT) Reasoning
Analyze step-by-step with high accuracy:
1. **Confirmed Bugs**: Definite syntax errors (missing colons, brackets), TypeErrors (string + int concatenation), NameErrors, IndexErrors.
2. **Edge Cases**: Empty collections (empty list [], empty dict {{}}, empty string ""), zero values, boundary conditions.
3. **Potential Assumptions / Clarifications**: Distinguish definite bugs from unspecified business rules. (e.g., a fixed discount vs percentage discount is a policy question to clarify, NOT a definite syntax or runtime error).
4. **Proportionality**: Do NOT invent enterprise security, multithreading, or logging issues unless they genuinely exist in the code.

### Output Structure:
1. **Defect Summary Table**:
   | Status | Category (Confirmed Bug / Potential Issue / Edge Case) | Error Type | Line / Snippet | Issue Description |
   (Use status: `[DETECTED]`)

2. **🛡️ Key Edge Cases & Potential Issues Explained**:
   - For each edge case:
     - **Scenario / Input**: What input triggers it (e.g., `prices = []`, `discount > total`).
     - **Behavior**: What happens (e.g., unhandled empty sum, negative total).
     - **Recommendation**: How the code should cleanly handle it.

3. **High-Level Takeaway**: 1-2 sentence concise summary.

Keep your explanations clear, simple, and direct.
"""

BUG_FINDER_USER_PROMPT = """Analyze this code for confirmed bugs, edge cases, and potential ambiguities.

### Submitted Code:
```{language}
{code}
```

### Reference Guidelines:
{rag_context}

Provide your structured defect analysis with clear edge case explanations:"""


class BugFinderAgent:
    """
    Bug-Finder Agent: Detects logical errors, edge-case failures, runtime risks,
    and distinguishes confirmed bugs from potential business assumptions.
    """

    PROMPT_TECHNIQUE = "Chain of Thought (CoT) Reasoning"

    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", BUG_FINDER_SYSTEM_PROMPT),
            ("user", BUG_FINDER_USER_PROMPT)
        ])
        # LCEL Chain: Prompt | Model | Parser
        self.chain = self.prompt_template | self.llm | StrOutputParser()

    def analyze(self, code: str, language: str = "python", rag_context: str = "") -> str:
        """Execute the bug finding chain."""
        return self.chain.invoke({
            "code": code,
            "language": language,
            "rag_context": rag_context if rag_context.strip() else "Standard Python safety specifications apply."
        })

    def get_prompt_metadata(self) -> Dict[str, str]:
        """Returns prompt telemetry for transparent evaluation."""
        return {
            "agent": "Bug-Finder Agent",
            "technique": self.PROMPT_TECHNIQUE,
            "system_prompt": BUG_FINDER_SYSTEM_PROMPT,
            "user_prompt_template": BUG_FINDER_USER_PROMPT
        }
