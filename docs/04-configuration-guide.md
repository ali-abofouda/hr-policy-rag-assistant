# Configuration Guide: Pydantic v2 Settings & Environment Validation

## 1. Overview

Application configuration is centralized in `src/core/config.py` using **Pydantic v2 `BaseSettings`** (`pydantic-settings`). This architecture eliminates error-prone `os.getenv()` calls across the codebase, enforces strict type validation, and verifies all required credentials during startup.

---

## 2. Environment Specification (`.env.example`)

```ini
# --- Google Cloud Platform & Storage ---
PROJECT_ID=rag-hr-assistant-local
LOCATION=us-central1
GCS_BUCKET_NAME=local-bucket

# --- Vector Database (Qdrant Cloud) ---
QDRANT_URL=https://0c4dcb16-fe28-4eca-bfbf-86fc6217460c.us-central1-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION_NAME=hr_policies
QDRANT_NOISY_COLLECTION_NAME=hr_policies_noisy_demo

# --- LLM Providers & Inference Router ---
GEMINI_API_KEY=your_gemini_api_key_here
LLM_MODEL_NAME=gemini-3.5-flash-lite
FALLBACK_MODEL_NAME=openai/gpt-oss-20b
GROQ_API_KEY=your_groq_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
JUDGE_MODEL_NAME=openai/gpt-oss-120b

# --- Embeddings & Re-ranker ---
JINA_API_KEY=your_jina_api_key_here
EMBEDDING_MODEL_NAME=jina-embeddings-v2-base-en
RERANKER_MODEL_NAME=jina-reranker-v2-base-multilingual

# --- Retrieval Parameters ---
CHUNK_SIZE=500
CHUNK_OVERLAP=60
TOP_K_RESULTS=5
RERANK_CANDIDATE_K=12
RELEVANCE_THRESHOLD=0.35

# --- Reliability & Safety Guardrails ---
GUARDRAIL_PROVIDER=gemini_lite
GUARDRAIL_OUTPUT_PROVIDER=local
GUARDRAIL_FAIL_OPEN_INPUT=false
GUARDRAIL_FAIL_OPEN_OUTPUT=true
GUARDRAIL_HISTORY_TURNS=6

# --- Semantic Cache ---
SEMANTIC_CACHE_THRESHOLD=0.80
SEMANTIC_CACHE_MAX_ENTRIES=500
SEMANTIC_CACHE_TTL_SECONDS=3600

# --- Observability (LangSmith) ---
LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=hr-policy-assistant

# --- Access Control & IAM ---
ALLOWED_EMPLOYEE_EMAILS=mentordivesh@gmail.com,aliashraf@example.com
```

---

## 3. Configuration Schema & Field Validators

The `Settings` class implements custom Pydantic validators to process complex environment variables:

```python
class Settings(BaseSettings):
    """Production configuration schema with strict environment validation."""

    PROJECT_NAME: str = Field(default="HR Policy Assistant RAG")
    API_VERSION: str = Field(default="1.0.0")
    
    # Dynamic parsing of comma-separated string to list
    ALLOWED_EMPLOYEE_EMAILS: Union[str, List[str]] = Field(default="mentordivesh@gmail.com")

    @field_validator("ALLOWED_EMPLOYEE_EMAILS", mode="after")
    @classmethod
    def parse_allowed_emails(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [email.strip().lower() for email in value.split(",") if email.strip()]
        return [str(e).strip().lower() for e in value if str(e).strip()]
```

### Path Resolution Logic:
The settings manager computes the absolute project root dynamically:
```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
```
This guarantees that unit tests, standalone CLI scripts, Docker containers, and web servers load the correct `.env` regardless of the shell's active working directory.
