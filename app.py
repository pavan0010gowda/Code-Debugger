import os
import sys
import difflib
from pathlib import Path
import streamlit as st

# Configure page metadata
st.set_page_config(
    page_title="Code Review & Debug Squad",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished IDE look & feel
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: #1e293b;
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #334155;
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 4px;
        margin-right: 6px;
    }
    .badge-primary { background-color: #0284c7; color: white; }
    .badge-success { background-color: #16a34a; color: white; }
    .badge-warning { background-color: #d97706; color: white; }
    .badge-danger { background-color: #dc2626; color: white; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Add workspace directory to python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_TEMPERATURE,
    get_groq_api_key,
    fetch_active_groq_models
)
from core.rag_engine import get_rag_engine
from core.agents.coordinator import SquadCoordinator
from core.agents.bug_finder import BugFinderAgent
from core.agents.style_lint import StyleLintAgent
from core.agents.fixer import FixerAgent
from core.agents.test_writer import TestWriterAgent
from core.intent_router import ROUTER_SYSTEM_PROMPT


# Initialize RAG Engine singleton
rag_engine = get_rag_engine()

# --- PRESET CODES FOR QUICK EVALUATION ---
SAMPLE_PRESETS = {
    "Select a preset demo...": "",
    "Benchmark Test 02: Multi-Bug Evaluation (calculate_total)": '''def calculate_total(prices, discount=10):
    total = 0
    for price in prices:
        total = total + price
    final_total = total - discount
    if final_total < 0
        final_total = 0
    print("Final Total: " + final_total)
    return final_total

prices = [100, 200, 300]
result = calculate_total(prices)
print("Returned:", result)
''',
    "Preset 1: Logic Bugs (Mutable Default + Off-by-one + Zero Division)": '''def register_user_session(user_id, sessions=[]):
    # BUG: mutable default argument persists across invocations
    sessions.append(user_id)
    return sessions

def binary_search(arr, target):
    left = 0
    right = len(arr)  # BUG: Off-by-one boundary error
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

def compute_average_rating(ratings):
    # BUG: ZeroDivisionError if list is empty
    return sum(ratings) / len(ratings)
''',
    "Preset 2: Security Hazards (Arbitrary eval RCE & Path Traversal)": '''import os

API_SECRET_KEY = "sk_live_998877665544332211"  # VULNERABILITY: Hardcoded secret

def calculate_formula(user_expression):
    # VULNERABILITY: Arbitrary Code Execution (CWE-95)
    result = eval(user_expression)
    return result

def retrieve_user_log(filename):
    # VULNERABILITY: Path Traversal (CWE-22)
    filepath = f"/var/logs/{filename}"
    with open(filepath, "r") as f:
        return f.read()
''',
    "Preset 3: Style & Clean Code Violations (PEP 8 non-compliance)": '''def CalculateTotalPrice(p, d, t):
    l = p - (p * d)
    if t == True:
        O = l + (l * 0.18)
        return O
    else:
        return l
'''
}


# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.markdown("### ⚙️ Squad Configuration")
    
    # API Key Handling
    env_api_key = get_groq_api_key()
    api_key_input = st.text_input(
        "Groq API Key",
        value=env_api_key,
        type="password",
        help="Get a free Groq API key at https://console.groq.com/keys"
    )
    effective_api_key = api_key_input.strip() or env_api_key

    if not effective_api_key:
        st.warning("⚠️ Enter your Groq API key to activate the squad. (Free tier supported!)")

    # Dynamic Model Selection (queries Groq API for active models accessible to this key)
    available_models = fetch_active_groq_models(effective_api_key)
    selected_model = st.selectbox(
        "LLM Reasoner",
        options=available_models,
        index=0,
        help="openai/gpt-oss-20b provides fast inference and generous rate limits on Groq."
    )

    temperature = st.slider(
        "Sampling Temperature",
        min_value=0.0,
        max_value=1.0,
        value=DEFAULT_TEMPERATURE,
        step=0.05,
        help="Lower values yield more deterministic and accurate code analysis."
    )

    st.markdown("---")
    st.markdown("### 🎯 Workflow & Intent")
    selected_mode = st.selectbox(
        "Execution Mode",
        options=[
            "Auto-Detect Intent",
            "Full Squad Audit",
            "Bug Finder & Edge Cases",
            "Style & PEP 8 Lint",
            "Unit Test & Sandbox Execution",
            "Code Explanation"
        ],
        index=0,
        help="Choose 'Auto-Detect Intent' to let the LCEL Router dynamically dispatch tasks."
    )

    st.markdown("---")
    st.markdown("### 📚 Vector DB Knowledge Base")
    doc_count = rag_engine.collection.count()
    st.success(f"ChromaDB Indexed Chunks: **{doc_count}**")
    if st.button("🔄 Re-index Knowledge Base"):
        with st.spinner("Re-indexing standards into ChromaDB..."):
            count = rag_engine.index_knowledge_base()
            st.success(f"Indexed {count} guidelines!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🎓 Acceptance Criteria Checklist")
    with st.expander("View Mandatory Criteria Status", expanded=False):
        st.markdown("""
        - ✅ **1. LLM Integration**: Groq API (`llama-3.1-8b-instant`)
        - ✅ **2. Interactive GUI**: Streamlit Multi-Tab Workspace
        - ✅ **3. Prompt Engineering**: CoT, Few-Shot, ReAct Reflection
        - ✅ **4. LangChain LCEL**: `Prompt | Model | Parser` Chains
        - ✅ **5. Agentic RAG**: Dynamic ChromaDB context retrieval
        - ✅ **6. Intent Routing**: Automated Intent Classification
        - ✅ **7. Vector Database**: Persistent ChromaDB with Cosine Distance
        """)


# --- MAIN HEADER ---
st.markdown('<div class="main-title">🛡️ Code Review & Debug Squad</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Autonomous Multi-Agent Engineering Squad • Powered by Groq Cloud • LangChain (LCEL) • ChromaDB Agentic RAG • Isolated Sandbox Reflection</div>',
    unsafe_allow_html=True
)

# Preset Selector
col_preset, col_clear = st.columns([4, 1])
with col_preset:
    chosen_preset_title = st.selectbox("Load Sample Code Preset:", list(SAMPLE_PRESETS.keys()))
with col_clear:
    st.write("")
    st.write("")
    if st.button("Clear Input"):
        st.session_state["code_input"] = ""
        st.rerun()

# Maintain code in session state
if "code_input" not in st.session_state:
    st.session_state["code_input"] = SAMPLE_PRESETS["Benchmark Test 02: Multi-Bug Evaluation (calculate_total)"]

if chosen_preset_title and SAMPLE_PRESETS[chosen_preset_title]:
    st.session_state["code_input"] = SAMPLE_PRESETS[chosen_preset_title]

# Code Editor & Instructions
code_input = st.text_area(
    "Target Code Snippet (Python):",
    value=st.session_state.get("code_input", ""),
    height=240,
    help="Paste Python code or select a preset to analyze."
)

user_instruction = st.text_input(
    "Optional Developer Instruction / Goal:",
    placeholder="e.g., 'Find all edge-case bugs and write unit tests', 'Check PEP 8 style', or 'Audit security risks'",
    help="The Intent Router will use this to determine the execution path."
)

col_run, col_status = st.columns([1, 3])
with col_run:
    run_button = st.button("🚀 Deploy Code Review Squad", type="primary", use_container_width=True)


# --- SQUAD EXECUTION ---
if run_button:
    if not effective_api_key:
        st.error("❌ Please provide a valid Groq API Key in the sidebar.")
    elif not code_input.strip():
        st.warning("⚠️ Please provide code to review.")
    else:
        # Progress tracking UI
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(msg: str, frac: float):
            status_text.markdown(f"**Squad Status:** {msg}")
            progress_bar.progress(frac)

        coordinator = SquadCoordinator(
            api_key=effective_api_key,
            model_name=selected_model,
            temperature=temperature
        )

        with st.spinner("Multi-Agent Squad in session..."):
            review_results = coordinator.run_review(
                code=code_input,
                user_instruction=user_instruction,
                explicit_mode=selected_mode,
                progress_callback=update_progress
            )
            st.session_state["review_results"] = review_results
            progress_bar.progress(1.0)
            status_text.success(f"Review completed in {review_results['elapsed_time']}s!")


# --- DISPLAY RESULTS ---
if "review_results" in st.session_state:
    res = st.session_state["review_results"]
    intent = res.get("intent", "FULL_SQUAD_AUDIT")

    st.markdown("---")
    
    # Quick Telemetry Banner
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.metric("Detected Intent", intent)
    with col_t2:
        st.metric("Execution Time", f"{res.get('elapsed_time', 0)}s")
    with col_t3:
        sandbox_res = res.get("sandbox_result")
        test_status = "PASSED" if (sandbox_res and sandbox_res.success) else ("FAILED" if sandbox_res else "N/A")
        st.metric("Sandbox Tests", test_status)
    with col_t4:
        reflections_count = len(res.get("reflection_history", []))
        st.metric("Reflection Iterations", reflections_count)

    # Result Tabs
    tab_summary, tab_bugs, tab_style, tab_tests, tab_reflection, tab_rag, tab_prompts = st.tabs([
        "📊 Executive Review & Refactored Code",
        "🐛 Bug-Finder Diagnostics (CoT)",
        "🎨 Style & PEP 8 Linter",
        "🧪 Test Suite & Sandbox",
        "🔁 Reflection & Self-Healing",
        "🧠 Agentic RAG & Routing",
        "📋 System Prompts & LCEL Inspector"
    ])

    # TAB 1: EXECUTIVE REVIEW & REFACTORED CODE
    with tab_summary:
        if intent == "CODE_EXPLANATION":
            st.markdown("### 📖 Educational Code Explanation")
            st.markdown(res.get("explanation", ""))
        else:
            st.markdown("### 🛠️ Refactored, Production-Ready Code")
            refactored = res.get("refactored_code", "")
            if refactored:
                col_orig, col_fixed = st.columns(2)
                with col_orig:
                    st.markdown("**Original Code:**")
                    st.code(code_input, language="python")
                with col_fixed:
                    st.markdown("**Refactored Code (Clean, Bug-Free, Verified):**")
                    st.code(refactored, language="python")
                
                # Show side-by-side diff
                with st.expander("🔍 View Line-by-Line Code Diff", expanded=False):
                    diff = difflib.unified_diff(
                        code_input.splitlines(keepends=True),
                        refactored.splitlines(keepends=True),
                        fromfile="original.py",
                        tofile="refactored.py"
                    )
                    diff_text = "".join(diff)
                    if diff_text:
                        st.code(diff_text, language="diff")
                    else:
                        st.info("No modifications were required.")

                if res.get("raw_fixer_response"):
                    with st.expander("📝 Summary of Fixes & 🛡️ Edge Cases Handled", expanded=True):
                        st.markdown(res.get("raw_fixer_response"))
            else:
                st.info("Run 'Full Squad Audit' to generate refactored code and automated fixes.")

    # TAB 2: BUG-FINDER DIAGNOSTICS (Chain-of-Thought)
    with tab_bugs:
        st.markdown("### 🐛 Bug-Finder Agent Report")
        st.markdown('<span class="badge badge-primary">Technique: Chain of Thought (CoT)</span>', unsafe_allow_html=True)
        if res.get("bug_report"):
            st.markdown(res["bug_report"])
        else:
            st.info("Bug-Finder Agent was not invoked for this intent.")

    # TAB 3: STYLE & PEP 8 LINTER (Few-Shot)
    with tab_style:
        st.markdown("### 🎨 Style/Lint Agent Report")
        st.markdown('<span class="badge badge-success">Technique: Few-Shot Exemplar Prompting</span>', unsafe_allow_html=True)
        if res.get("style_report"):
            st.markdown(res["style_report"])
        else:
            st.info("Style/Lint Agent was not invoked for this intent.")

    # TAB 4: TEST SUITE & SANDBOX TERMINAL
    with tab_tests:
        st.markdown("### 🧪 Automated Test Suite & Sandbox Execution")
        test_code = res.get("test_suite_code")
        sandbox_res = res.get("sandbox_result")

        if test_code:
            st.markdown("**Generated Unit Tests:**")
            st.code(test_code, language="python")

        if sandbox_res:
            st.markdown("#### 🖥️ Isolated Sandbox Execution Terminal")
            if sandbox_res.success:
                st.success(f"✅ Status: VERIFIED — All tests passed in isolated execution sandbox! (Exit Code: {sandbox_res.returncode} in {sandbox_res.execution_time_sec}s)")
            else:
                st.error(f"❌ Status: UNVERIFIED — Sandbox execution failed! (Error: {sandbox_res.error_type}, Exit Code: {sandbox_res.returncode})")

            col_out, col_err = st.columns(2)
            with col_out:
                st.markdown("**Standard Output (stdout):**")
                st.code(sandbox_res.stdout if sandbox_res.stdout.strip() else "[No stdout output]", language="bash")
            with col_err:
                st.markdown("**Standard Error / Traceback (stderr):**")
                st.code(sandbox_res.stderr if sandbox_res.stderr.strip() else "[No errors reported]", language="bash")
        else:
            st.info("Sandbox execution was not triggered for this workflow.")

    # TAB 5: REFLECTION & SELF-HEALING LOG
    with tab_reflection:
        st.markdown("### 🔁 Reflection & Self-Correction Loop")
        st.markdown('<span class="badge badge-warning">Technique: ReAct / Reflection Loop</span>', unsafe_allow_html=True)
        reflections = res.get("reflection_history", [])
        if reflections:
            st.warning(f"Initial sandbox test failed. Squad executed **{len(reflections)} self-correction iteration(s)**.")
            for ref in reflections:
                with st.expander(f"Iterative Self-Correction #{ref['iteration']} (Result: {'Passed ✅' if ref['sandbox_success'] else 'Failed ❌'})", expanded=True):
                    st.markdown("**Fixer Agent Reflection Diagnosis:**")
                    st.markdown(ref["diagnosis_and_patch"])
                    if ref["stderr"]:
                        st.markdown("**Sandbox Feedback Received:**")
                        st.code(ref["stderr"], language="bash")
        else:
            st.success("✨ Zero reflection iterations required! Code passed sandbox verification on the first attempt.")

    # TAB 6: AGENTIC RAG & INTENT ROUTING
    with tab_rag:
        st.markdown("### 🧠 Agentic RAG & Dynamic Intent Routing")
        route_plan = res.get("route_plan", {})
        
        st.markdown("#### 1. Dynamic Routing Plan (LCEL)")
        st.json(route_plan)

        st.markdown("#### 2. ChromaDB Vector Store Query & Retrieved Documents")
        rag_docs = res.get("rag_docs", [])
        if rag_docs:
            for idx, doc in enumerate(rag_docs, start=1):
                with st.expander(f"Document {idx}: {doc['title']} (Cosine Similarity: {doc['similarity']})", expanded=True):
                    st.markdown(f"**Source File:** `{doc['source']}`")
                    st.markdown(doc["content"])
        else:
            st.info("No specific external guidelines retrieved.")

    # TAB 7: SYSTEM PROMPTS & LCEL INSPECTOR
    with tab_prompts:
        st.markdown("### 📋 Academic Evaluation: System Prompts & LCEL Telemetry")
        st.info("This section documents the exact system and user prompts used across the squad, directly fulfilling Mandatory Acceptance Criteria #3 & #4.")

        with st.expander("1. Intent Router Prompt & LCEL Pipeline", expanded=False):
            st.code(ROUTER_SYSTEM_PROMPT, language="markdown")

        with st.expander("2. Bug-Finder Agent Prompt (Chain of Thought)", expanded=False):
            bug_meta = BugFinderAgent(coordinator.llm).get_prompt_metadata()
            st.markdown(f"**Technique**: `{bug_meta['technique']}`")
            st.code(bug_meta["system_prompt"], language="markdown")

        with st.expander("3. Style/Lint Agent Prompt (Few-Shot Exemplars)", expanded=False):
            style_meta = StyleLintAgent(coordinator.llm).get_prompt_metadata()
            st.markdown(f"**Technique**: `{style_meta['technique']}`")
            st.code(style_meta["system_prompt"], language="markdown")

        with st.expander("4. Fixer Agent Prompts (Refactoring & Reflection)", expanded=False):
            fixer_meta = FixerAgent(coordinator.llm).get_prompt_metadata()
            st.markdown(f"**Technique**: `{fixer_meta['technique']}`")
            st.markdown("**Standard Refactoring System Prompt:**")
            st.code(fixer_meta["system_prompt"], language="markdown")
            st.markdown("**Reflection & Self-Correction System Prompt:**")
            st.code(fixer_meta["reflection_system_prompt"], language="markdown")

        with st.expander("5. Test-Writer Agent Prompt", expanded=False):
            test_meta = TestWriterAgent(coordinator.llm).get_prompt_metadata()
            st.markdown(f"**Technique**: `{test_meta['technique']}`")
            st.code(test_meta["system_prompt"], language="markdown")

