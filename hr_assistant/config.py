"""01 · config — Centralized configuration bridged to src.core.config.settings.

Provides 100% backward compatibility for all legacy tests, modules, and scripts.
"""

from typing import List, Tuple
from src.core.config import settings

# Core & Infrastructure
PROJECT_ID: str = settings.PROJECT_ID
LOCATION: str = settings.LOCATION

# API Keys & Endpoints
GEMINI_API_KEY: str = settings.GEMINI_API_KEY
JINA_API_KEY: str = settings.JINA_API_KEY
QDRANT_URL: str = settings.QDRANT_URL
QDRANT_API_KEY: str = settings.QDRANT_API_KEY

# Storage Zones
GCS_BUCKET_NAME: str = settings.GCS_BUCKET_NAME
GCS_PREFIX: str = settings.GCS_PREFIX
NOISE_GCS_PREFIX: str = settings.NOISE_GCS_PREFIX
PROCESSED_HR_PREFIX: str = settings.PROCESSED_HR_PREFIX
PROCESSED_NOISE_PREFIX: str = settings.PROCESSED_NOISE_PREFIX

# Collections
QDRANT_COLLECTION_NAME: str = settings.QDRANT_COLLECTION_NAME
QDRANT_NOISY_COLLECTION_NAME: str = settings.QDRANT_NOISY_COLLECTION_NAME

# Models & Gateways
LLM_MODEL_NAME: str = settings.LLM_MODEL_NAME
FALLBACK_MODEL_NAME: str = settings.FALLBACK_MODEL_NAME
GROQ_API_KEY: str = settings.GROQ_API_KEY
GROQ_BASE_URL: str = settings.GROQ_BASE_URL
JUDGE_MODEL_NAME: str = settings.JUDGE_MODEL_NAME

# Embeddings & Reranker
EMBEDDING_MODEL_NAME: str = settings.EMBEDDING_MODEL_NAME
RERANKER_MODEL_NAME: str = settings.RERANKER_MODEL_NAME

# Splitting & Retrieval
CHUNK_SIZE: int = settings.CHUNK_SIZE
CHUNK_OVERLAP: int = settings.CHUNK_OVERLAP
TOP_K_RESULTS: int = settings.TOP_K_RESULTS
RERANK_CANDIDATE_K: int = settings.RERANK_CANDIDATE_K

# Guardrails & Scope
HR_POLICY_CATEGORIES = settings.HR_POLICY_CATEGORIES
RELEVANCE_THRESHOLD: float = settings.RELEVANCE_THRESHOLD
GUARDRAIL_PROVIDER: str = settings.GUARDRAIL_PROVIDER
GUARDRAIL_OUTPUT_PROVIDER: str = settings.GUARDRAIL_OUTPUT_PROVIDER
GUARDRAIL_FAIL_OPEN_INPUT: bool = settings.GUARDRAIL_FAIL_OPEN_INPUT
GUARDRAIL_FAIL_OPEN_OUTPUT: bool = settings.GUARDRAIL_FAIL_OPEN_OUTPUT
GUARDRAIL_HISTORY_TURNS: int = settings.GUARDRAIL_HISTORY_TURNS

# Semantic Cache
SEMANTIC_CACHE_THRESHOLD: float = settings.SEMANTIC_CACHE_THRESHOLD
SEMANTIC_CACHE_MAX_ENTRIES: int = settings.SEMANTIC_CACHE_MAX_ENTRIES
SEMANTIC_CACHE_TTL_SECONDS: int = settings.SEMANTIC_CACHE_TTL_SECONDS

# LangSmith Tracing
LANGSMITH_TRACING: str = settings.LANGSMITH_TRACING
LANGSMITH_ENDPOINT: str = settings.LANGSMITH_ENDPOINT
LANGSMITH_API_KEY: str = settings.LANGSMITH_API_KEY
LANGSMITH_PROJECT: str = settings.LANGSMITH_PROJECT

# Access Control
ALLOWED_EMPLOYEE_EMAILS: List[str] = settings.ALLOWED_EMPLOYEE_EMAILS


def check_api_keys() -> None:
    """Validate required API keys using the Pydantic settings validator."""
    settings.check_api_keys()
