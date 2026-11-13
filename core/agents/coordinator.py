import time
from typing import Dict, Any, Optional, Callable
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.agents.bug_finder import BugFinderAgent
from core.agents.style_lint import StyleLintAgent
from core.agents.fixer import FixerAgent
from core.agents.test_writer import TestWriterAgent
from core.sandbox import CodeExecutionSandbox, SandboxResult
from core.rag_engine import get_rag_engine
from core.intent_router import IntentRouter
from core.config import DEFAULT_GROQ_MODEL, MAX_REFLECTION_ITERATIONS, MAX_TOKENS


EXPLAINER_PROMPT = """You are a Code Educator. Explain this code simply, concisely, and in plain English:
1. **What This Code Does**: 1-2 sentence high-level summary.
2. **How It Works**: 3-4 short, clear bullet points explaining the core flow.
3. **🛡️ Key Edge Cases to Watch**: Explain the critical edge cases (empty collections, zero inputs, off-by-one boundaries).
4. **Complexity in Simple Terms**: Time & memory complexity in 1 sentence each.

Keep the explanation short, crisp, and beginner-friendly.

Code:
```{language}
{code}
```
"""


class SquadCoordinator:
    """
    Orchestrator for the Code Review & Debug Squad.
    Coordinates Intent Detection, Agentic RAG from ChromaDB, multi-agent analysis,
    isolated sandbox execution, and the Reflection / Self-Correction loop.
    Includes rate-limit resilience and automatic model fallback.
    """

    def __init__(self, api_key: str, model_name: str = DEFAULT_GROQ_MODEL, temperature: float = 0.2):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self._init_agents(model_name)
        self.sandbox = CodeExecutionSandbox(timeout_sec=8)
        self.rag_engine = get_rag_engine()

    def _init_agents(self, model: str):
        """Initialize or rebind agents to a specific LLM model."""
        self.model_name = model
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name=model,
            temperature=self.temperature,
            max_tokens=MAX_TOKENS
        )
        self.bug_finder = BugFinderAgent(self.llm)
        self.style_linter = StyleLintAgent(self.llm)
        self.fixer = FixerAgent(self.llm)
        self.test_writer = TestWriterAgent(self.llm)
        self.router = IntentRouter(self.llm)

    def _safe_invoke(self, fn: Callable, *args, **kwargs):
        """Execute agent invocation with automatic backoff retry if Groq TPM limit is touched."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str:
                    wait_sec = 4 * (attempt + 1)
                    time.sleep(wait_sec)
                    if attempt == max_attempts - 1:
                        raise e
                else:
                    raise e

    def _ensure_active_model(self, notify: Callable[[str, float], None]):
        """Verify model accessibility; seamlessly fallback if 404 occurs."""
        try:
            # Lightweight probe
            self.llm.invoke("Ping")
        except Exception as e:
            err_msg = str(e).lower()
            if "not exist" in err_msg or "not_found" in err_msg or "access to it" in err_msg:
                fallback_model = DEFAULT_GROQ_MODEL
                if self.model_name != fallback_model:
                    notify(f"Selected model '{self.model_name}' unavailable. Auto-switching to '{fallback_model}'...", 0.05)
                    self._init_agents(fallback_model)

    def run_review(
        self,
        code: str,
        user_instruction: str = "",
        explicit_mode: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute full squad review or targeted intent pipeline.
        """
        start_time = time.perf_counter()
        telemetry = {
            "model_used": self.model_name,
            "steps_executed": [],
            "rag_docs_retrieved": [],
            "reflection_history": []
        }

        def notify(step_name: str, fraction: float):
            telemetry["steps_executed"].append(step_name)
            if progress_callback:
                progress_callback(step_name, fraction)

        # 0. Model Probe & Auto-Fallback Check
        self._ensure_active_model(notify)
        telemetry["model_used"] = self.model_name

        # 1. Intent Detection & Routing (Mandatory Acceptance Criteria #6 & #4)
        notify("Analyzing Intent & Planning Squad Routing...", 0.10)
        route_plan = self.router.route(user_instruction, code, explicit_mode)
        intent = route_plan.get("intent", "FULL_SQUAD_AUDIT")

        # 2. Agentic RAG Decision & Context Retrieval (Mandatory Acceptance Criteria #5 & #7)
        rag_query = route_plan.get("recommended_rag_query", user_instruction or "Clean code and bug prevention standards")
        notify(f"Querying ChromaDB Vector Store for '{rag_query}'...", 0.20)
        
        retrieved_docs = self.rag_engine.retrieve(rag_query, top_k=3)
        formatted_rag_context = self.rag_engine.format_retrieved_context(retrieved_docs)
        telemetry["rag_docs_retrieved"] = retrieved_docs

        # 3. Dispatch based on Intent
        if intent == "CODE_EXPLANATION":
            notify("Generating Simple & Clear Code Explanation...", 0.60)
            explainer_chain = (
                ChatPromptTemplate.from_messages([("system", EXPLAINER_PROMPT)])
                | self.llm
                | StrOutputParser()
            )
            explanation = self._safe_invoke(explainer_chain.invoke, {"code": code, "language": "python"})
            notify("Review Complete!", 1.0)
            return {
                "intent": intent,
                "route_plan": route_plan,
                "rag_docs": retrieved_docs,
                "explanation": explanation,
                "elapsed_time": round(time.perf_counter() - start_time, 2),
                "telemetry": telemetry
            }

        bug_report = ""
        style_report = ""
        refactored_code = ""
        raw_fixer_response = ""
        test_suite_code = ""
        sandbox_result: Optional[SandboxResult] = None
        reflection_history = []

        # Step A: Bug Finder Agent (Chain-of-Thought)
        if intent in ["FULL_SQUAD_AUDIT", "BUG_DETECTION"]:
            notify("Bug-Finder Agent: Analyzing Edge Cases & Bugs...", 0.35)
            bug_report = self._safe_invoke(self.bug_finder.analyze, code, rag_context=formatted_rag_context)
            time.sleep(1.0)  # Rate limit breathing room

        # Step B: Style/Lint Agent (Few-Shot Prompting)
        if intent in ["FULL_SQUAD_AUDIT", "STYLE_LINT"]:
            notify("Style/Lint Agent: Checking Clean Code & PEP 8 Hygiene...", 0.50)
            style_report = self._safe_invoke(self.style_linter.analyze, code, rag_context=formatted_rag_context)
            time.sleep(1.0)  # Rate limit breathing room

        # Step C: Fixer Agent (Simple Refactoring)
        if intent == "FULL_SQUAD_AUDIT":
            notify("Fixer Agent: Creating Simple, Bug-Free Code & Edge Case Notes...", 0.65)
            raw_fixer_response = self._safe_invoke(
                self.fixer.refactor,
                code=code,
                bug_report=bug_report,
                style_report=style_report,
                rag_context=formatted_rag_context
            )
            refactored_code = self.fixer.extract_python_code(raw_fixer_response)
            time.sleep(1.0)

        # Step D: Test-Writer Agent & Sandbox Verification
        if intent in ["FULL_SQUAD_AUDIT", "TEST_GENERATION"]:
            target_code_for_test = refactored_code if refactored_code else code
            notify("Test-Writer Agent: Generating Deterministic Test Suite...", 0.75)
            test_response = self._safe_invoke(self.test_writer.generate_tests, target_code_for_test, bug_context=bug_report)
            test_suite_code = self.test_writer.extract_python_tests(test_response)

            # Step E: Sandbox Execution
            notify("Execution Sandbox: Executing Test Suite in Isolated Subprocess...", 0.85)
            sandbox_result = self.sandbox.execute(code=target_code_for_test, test_code=test_suite_code)

            # Step F: Reflection & Self-Correction Loop (ReAct / Reflection)
            if intent == "FULL_SQUAD_AUDIT" and not sandbox_result.success:
                reflection_iteration = 0
                current_code = target_code_for_test
                current_error = sandbox_result.stderr or sandbox_result.stdout

                while not sandbox_result.success and reflection_iteration < MAX_REFLECTION_ITERATIONS:
                    reflection_iteration += 1
                    notify(f"Self-Correction Reflection Loop [Iteration {reflection_iteration}]: Diagnosing Sandbox Failure...", 0.90)

                    correction_response = self._safe_invoke(
                        self.fixer.reflect_and_correct,
                        current_code=current_code,
                        test_code=test_suite_code,
                        sandbox_error=current_error
                    )
                    corrected_code = self.fixer.extract_python_code(correction_response)
                    
                    # Re-run sandbox with updated code
                    sandbox_result = self.sandbox.execute(code=corrected_code, test_code=test_suite_code)
                    
                    reflection_record = {
                        "iteration": reflection_iteration,
                        "diagnosis_and_patch": correction_response,
                        "sandbox_success": sandbox_result.success,
                        "returncode": sandbox_result.returncode,
                        "stderr": sandbox_result.stderr
                    }
                    reflection_history.append(reflection_record)
                    telemetry["reflection_history"].append(reflection_record)

                    if sandbox_result.success:
                        refactored_code = corrected_code
                        break
                    else:
                        current_code = corrected_code
                        current_error = sandbox_result.stderr or sandbox_result.stdout

        notify("Squad Review Successfully Finalized!", 1.0)
        elapsed_total = round(time.perf_counter() - start_time, 2)

        return {
            "intent": intent,
            "route_plan": route_plan,
            "rag_docs": retrieved_docs,
            "rag_context": formatted_rag_context,
            "bug_report": bug_report,
            "style_report": style_report,
            "refactored_code": refactored_code,
            "raw_fixer_response": raw_fixer_response,
            "test_suite_code": test_suite_code,
            "sandbox_result": sandbox_result,
            "reflection_history": reflection_history,
            "elapsed_time": elapsed_total,
            "telemetry": telemetry
        }
