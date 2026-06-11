"""Central configuration — reads from environment / .env via python-dotenv."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_PATH = Path(os.getenv("KNOWLEDGE_BASE_PATH", ROOT_DIR / "knowledge" / "raw"))
CHROMA_DB_PATH = Path(os.getenv("CHROMA_DB_PATH", ROOT_DIR / "knowledge" / "chromadb"))
PROCESSED_DOCS_PATH = Path(os.getenv("PROCESSED_DOCS_PATH", ROOT_DIR / "knowledge" / "processed"))
LOG_DIR = Path(os.getenv("LOG_DIR", ROOT_DIR / "logs"))
DATA_DIR = ROOT_DIR / "data"

# ── LLM ───────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Optional: OpenAI-compatible base URL (e.g. Vocarium, Azure OpenAI). Leave empty for default.
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o")
SAFETY_MODEL = os.getenv("SAFETY_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ── RAG ───────────────────────────────────────────────────────────────────────
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
CHROMA_COLLECTION_NAME = "loan_policies"

# ── Agent ─────────────────────────────────────────────────────────────────────
MEMORY_WINDOW = int(os.getenv("MEMORY_WINDOW", "10"))
MAX_ITERATIONS = 10

# ── Observability ─────────────────────────────────────────────────────────────
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = (
    os.getenv("LANGFUSE_HOST")
    or os.getenv("LANGFUSE_BASE_URL")
    or "https://cloud.langfuse.com"
)

# ── Deployment ────────────────────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8080"))

# ── Loan product ceilings (advisory escalation threshold) ─────────────────────
ESCALATION_CEILINGS = {
    "home_loan":     1_50_00_000,   # ₹1.5 Cr
    "personal_loan":   40_00_000,   # ₹40 L
    "msme_loan":     2_00_00_000,   # ₹2 Cr
    "car_loan":        20_00_000,   # ₹20 L
}

# ── Safety ────────────────────────────────────────────────────────────────────
SAFETY_SCORE_THRESHOLD = 0.7  # Langfuse LLM-as-judge minimum pass score
