import json
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from core.config import DEFAULT_GROQ_MODEL, FAST_GROQ_MODEL


ROUTER_SYSTEM_PROMPT = """You are the Lead Technical Dispatcher for an Autonomous Multi-Agent Code Review Squad.
Your role is to analyze developer requests, code characteristics, and determine the exact workflow routing.

Available Workflow Modes:
1. FULL_SQUAD_AUDIT: Comprehensive review involving Bug-Finder, Style/Lint, RAG Standards Retrieval, Fixer refactoring, Test generation, and Sandbox verification. (Default when user wants full review, or when no specific mode is mentioned).
2. BUG_DETECTION: Focus specifically on runtime bugs, logical errors, edge cases, vulnerabilities, and off-by-one errors.
3. STYLE_LINT: Focus specifically on PEP 8 formatting, naming conventions, docstrings, readability, and clean code hygiene.
4. TEST_GENERATION: Focus specifically on generating comprehensive unit tests and verifying them inside the execution sandbox.
5. CODE_EXPLANATION: Focus on breaking down the algorithm step-by-step, explaining time/space complexity, and architecture.

You MUST respond strictly in valid JSON format matching this schema:
{{
    "intent": "<FULL_SQUAD_AUDIT | BUG_DETECTION | STYLE_LINT | TEST_GENERATION | CODE_EXPLANATION>",
    "confidence": <float between 0.0 and 1.0>,
    "reasoning": "<Short 1-2 sentence explanation of why this route was chosen>",
    "recommended_rag_query": "<Specific query to search the Vector DB for, e.g. 'mutable default argument pitfall', 'eval arbitrary code injection', or 'pep8 naming conventions'>",
    "agents_to_invoke": ["<agent names>"]
}}
"""

class IntentRouter:
    """
    LCEL-based Intent Detection and Dynamic Routing Engine.
    Identifies user goals and routes to the proper agent pipeline or tool execution path.
    """

    def __init__(self, llm: Optional[ChatGroq] = None):
        self.llm = llm

    def _build_lcel_chain(self):
        """Construct the LangChain Expression Language (LCEL) chain."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", ROUTER_SYSTEM_PROMPT),
            (
                "user",
                "User Request / Goal: {user_instruction}\n\n"
                "Target Code (first 30 lines):\n```\n{code_preview}\n```\n\n"
                "Determine the intent and respond strictly with the JSON object."
            )
        ])
        # LCEL Composition: Prompt | Model | OutputParser
        return prompt | self.llm | StrOutputParser()

    def route(self, user_instruction: str, code: str, explicit_mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify intent and generate dynamic dispatch plan.
        If explicit_mode is chosen by user in GUI, respect it but still enrich with RAG query.
        """
        code_preview = "\n".join(code.strip().splitlines()[:30])
        
        # If user explicitly selected a mode in the dropdown, construct default dispatch
        if explicit_mode and explicit_mode != "Auto-Detect Intent":
            mode_mapping = {
                "Full Squad Audit": "FULL_SQUAD_AUDIT",
                "Bug Finder & Edge Cases": "BUG_DETECTION",
                "Style & PEP 8 Lint": "STYLE_LINT",
                "Unit Test & Sandbox Execution": "TEST_GENERATION",
                "Code Explanation": "CODE_EXPLANATION"
            }
            intent = mode_mapping.get(explicit_mode, "FULL_SQUAD_AUDIT")
            return {
                "intent": intent,
                "confidence": 1.0,
                "reasoning": f"User explicitly selected mode: {explicit_mode}",
                "recommended_rag_query": user_instruction or "Clean code and bug prevention standards",
                "agents_to_invoke": self._get_agents_for_intent(intent)
            }

        # If LLM is available, run LCEL Intent Classifier
        if self.llm:
            try:
                chain = self._build_lcel_chain()
                raw_response = chain.invoke({
                    "user_instruction": user_instruction if user_instruction.strip() else "Perform standard code review",
                    "code_preview": code_preview
                })

                # Clean markdown JSON wrapping if present
                clean_json = raw_response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                
                parsed = json.loads(clean_json.strip())
                parsed["agents_to_invoke"] = self._get_agents_for_intent(parsed.get("intent", "FULL_SQUAD_AUDIT"))
                return parsed
            except Exception as e:
                pass

        # Fallback heuristic routing
        return self._heuristic_routing(user_instruction)

    def _get_agents_for_intent(self, intent: str) -> list:
        if intent == "BUG_DETECTION":
            return ["Bug-Finder Agent"]
        elif intent == "STYLE_LINT":
            return ["Style/Lint Agent"]
        elif intent == "TEST_GENERATION":
            return ["Test-Writer Agent", "Execution Sandbox"]
        elif intent == "CODE_EXPLANATION":
            return ["Code Explainer Agent"]
        else: # FULL_SQUAD_AUDIT
            return ["Bug-Finder Agent", "Style/Lint Agent", "Fixer Agent", "Test-Writer Agent", "Execution Sandbox"]

    def _heuristic_routing(self, instruction: str) -> Dict[str, Any]:
        inst_lower = instruction.lower()
        if any(w in inst_lower for w in ["test", "unittest", "pytest", "sandbox", "verify"]):
            intent = "TEST_GENERATION"
        elif any(w in inst_lower for w in ["style", "pep8", "lint", "format", "naming", "clean"]):
            intent = "STYLE_LINT"
        elif any(w in inst_lower for w in ["bug", "error", "fix runtime", "crash", "off-by-one", "exception"]):
            intent = "BUG_DETECTION"
        elif any(w in inst_lower for w in ["explain", "understand", "walkthrough", "complexity"]):
            intent = "CODE_EXPLANATION"
        else:
            intent = "FULL_SQUAD_AUDIT"

        return {
            "intent": intent,
            "confidence": 0.85,
            "reasoning": f"Heuristic pattern match on user instruction keyword.",
            "recommended_rag_query": instruction if instruction.strip() else "python programming standards and bug prevention",
            "agents_to_invoke": self._get_agents_for_intent(intent)
        }

