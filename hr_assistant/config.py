"""01 · config — Centralized configuration loaded from .env.

This module holds all configuration constants (keys, URLs, model IDs, chunk sizes).
All other pipeline components import settings from here.
"""

import os
from typing import List, Tuple
from dotenv import load_dotenv

# Load secrets and overrides from local project .env file
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_ENV = os.path.join(_PROJECT_ROOT, ".env")
if os.path.exists(_LOCAL_ENV):
    load_dotenv(dotenv_path=_LOCAL_ENV)
else:
    load_dotenv()

## ---------------------------------------------------------------------------
## 1. Google Cloud Platform & Core Settings
## ---------------------------------------------------------------------------
PROJECT_ID: str = os.getenv("PROJECT_ID", "rag-hr-assistant-demo")
LOCATION: str = os.getenv("LOCATION", "us-central1")

## ---------------------------------------------------------------------------
## 2. API Keys & Database Endpoints
## ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
JINA_API_KEY: str = os.getenv("JINA_API_KEY", "")
QDRANT_URL: str = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

## ---------------------------------------------------------------------------
## 3. Storage Hierarchy & Zones (Cloud & Local)
## ---------------------------------------------------------------------------
GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "rag-hr-assistant-demo-hr-policies")

# Raw Zone: Original source files
GCS_PREFIX: str = "raw/hr-policies/"
NOISE_GCS_PREFIX: str = "raw/other-data/"

# Processed Zone: Standardized parsed JSON records
PROCESSED_HR_PREFIX: str = "processed/hr-policies/"
PROCESSED_NOISE_PREFIX: str = "processed/other-data/"

## ---------------------------------------------------------------------------
## 4. Qdrant Collections
## ---------------------------------------------------------------------------
# Clean production collection
QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "hr_policies")

# Mixed collection (HR + non-HR noise) for stress testing
QDRANT_NOISY_COLLECTION_NAME: str = os.getenv("QDRANT_NOISY_COLLECTION_NAME", "hr_policies_noisy_demo")

## ---------------------------------------------------------------------------
## 5. Model Identifiers & LLM Gateway (LiteLLM)
## ---------------------------------------------------------------------------
# Primary inference model
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-3.5-flash-lite")

# Fallback inference model via Groq router
FALLBACK_MODEL_NAME: str = os.getenv("FALLBACK_MODEL_NAME", "llama-3.3-70b-versatile")

# Groq endpoint & judge model
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
JUDGE_MODEL_NAME: str = os.getenv("JUDGE_MODEL_NAME", "llama-3.3-70b-versatile")

# Embedding model: 768 dimensions
EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "jina-embeddings-v2-base-en")

# Cross-Encoder re-ranker model
RERANKER_MODEL_NAME: str = os.getenv("RERANKER_MODEL_NAME", "jina-reranker-v2-base-multilingual")

## ---------------------------------------------------------------------------
## 6. Text Chunking & Splitting Parameters
## ---------------------------------------------------------------------------
CHUNK_SIZE: int = 500
CHUNK_OVERLAP: int = 60

## ---------------------------------------------------------------------------
## 7. Two-Stage Retrieval Parameters
## ---------------------------------------------------------------------------
TOP_K_RESULTS: int = 5         # Final cited chunks passed to LLM context
RERANK_CANDIDATE_K: int = 12   # Wider candidate shortlist before re-ranking

## ---------------------------------------------------------------------------
## 8. Reliability — Scope Guardrail (Category Filter & Relevance Threshold)
## ---------------------------------------------------------------------------
HR_POLICY_CATEGORIES = {
    "Leave", "Work From Home", "Probation", "Notice Period", "Reimbursement",
    "Code of Conduct", "Holidays", "Maternity Paternity", "Travel Expense", "Exit Process",
}
RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.35"))

## ---------------------------------------------------------------------------
## 9. Reliability — Input & Output Safety Guardrails
## ---------------------------------------------------------------------------
GUARDRAIL_PROVIDER: str = os.getenv("GUARDRAIL_PROVIDER", "local")
GUARDRAIL_FAIL_OPEN_INPUT: bool = os.getenv("GUARDRAIL_FAIL_OPEN_INPUT", "false").strip().lower() == "true"
GUARDRAIL_FAIL_OPEN_OUTPUT: bool = os.getenv("GUARDRAIL_FAIL_OPEN_OUTPUT", "true").strip().lower() == "true"
GUARDRAIL_HISTORY_TURNS: int = int(os.getenv("GUARDRAIL_HISTORY_TURNS", "6"))

## ---------------------------------------------------------------------------
## 10. Reliability — Semantic Cache
## ---------------------------------------------------------------------------
SEMANTIC_CACHE_THRESHOLD: float = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.93"))
SEMANTIC_CACHE_MAX_ENTRIES: int = int(os.getenv("SEMANTIC_CACHE_MAX_ENTRIES", "500"))
SEMANTIC_CACHE_TTL_SECONDS: int = int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", "3600"))

## ---------------------------------------------------------------------------
## 11. LangSmith Observability & Tracing
## ---------------------------------------------------------------------------
LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "false")
LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "hr-policy-assistant")


def check_api_keys() -> None:
    """Validate that mandatory database endpoints and credentials are configured.
    
    QDRANT_URL, QDRANT_API_KEY, and GEMINI_API_KEY are required for standard execution.
    GROQ_API_KEY is optional for automated fallback routing and evaluation judging.

    Raises:
        ValueError: If mandatory vector store or LLM settings are missing from environment.
    """
    required_configs: List[Tuple[str, str]] = [
        ("QDRANT_URL", QDRANT_URL),
        ("QDRANT_API_KEY", QDRANT_API_KEY),
        ("GEMINI_API_KEY", GEMINI_API_KEY),
    ]
    missing = [name for name, value in required_configs if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

