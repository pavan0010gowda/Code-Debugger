import os
from pathlib import Path

# Suppress heavy TensorFlow/OneDNN overhead on startup
os.environ["USE_TF"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

# Default Groq LLM Configuration
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
FAST_GROQ_MODEL = "openai/gpt-oss-20b"

FALLBACK_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
    "allam-2-7b",
    "qwen/qwen3.8-27b"
]

DEFAULT_TEMPERATURE = 0.2
MAX_TOKENS = 1500

# Sandbox execution settings
SANDBOX_TIMEOUT_SECONDS = 8
MAX_REFLECTION_ITERATIONS = 2

def get_groq_api_key() -> str:
    """Retrieve Groq API key from environment or return empty string."""
    return os.getenv("GROQ_API_KEY", "").strip()

def fetch_active_groq_models(api_key: str) -> list:
    """
    Dynamically fetch the exact active models available to this specific API key.
    Falls back to robust curated list if API call fails or key is empty.
    """
    if not api_key:
        return FALLBACK_MODELS

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        model_list = client.models.list()
        
        # Exclude audio/guardrail models from code review chat selection
        active_ids = [
            m.id for m in model_list.data
            if not m.id.startswith("whisper") 
            and "guard" not in m.id.lower()
            and not m.id.startswith("orpheus")
        ]
        
        if active_ids:
            # Sort prioritized models to the top (openai/gpt-oss-20b, openai/gpt-oss-120b)
            # and push low-rate-limit models (like Qwen with 1000 OTPM limit) to the bottom
            priority_order = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]
            sorted_models = []
            for p in priority_order:
                if p in active_ids:
                    sorted_models.append(p)
                    active_ids.remove(p)
            sorted_models.extend(active_ids)
            return sorted_models
    except Exception as err:
        _ = err
        return FALLBACK_MODELS
    
    return FALLBACK_MODELS
