"""backend/app/core/config.py — Centralized Enterprise Settings powered by Pydantic v2."""

import os
from pathlib import Path
from typing import List, Set, Tuple, Union
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate .env by searching current directory and parents up to 4 levels
_CURRENT = Path(__file__).resolve().parent
_ENV_PATH = None
for parent in [_CURRENT, _CURRENT.parent, _CURRENT.parent.parent, _CURRENT.parent.parent.parent]:
    candidate = parent / ".env"
    if candidate.exists():
        _ENV_PATH = candidate
        break

if _ENV_PATH and _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()


class Settings(BaseSettings):
    """Production configuration schema with strict environment validation."""

    # 1. Application & Environment Metadata
    PROJECT_NAME: str = Field(default="HR Policy Assistant RAG")
    API_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    CORS_ORIGINS: Union[str, List[str]] = Field(default="*")

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return list(value)

    # 2. GCP Project Metadata & Storage Hierarchy
    PROJECT_ID: str = Field(default="rag-hr-assistant-local")
    LOCATION: str = Field(default="us-central1")
    GCS_BUCKET_NAME: str = Field(default="local-bucket")
    GCS_PREFIX: str = Field(default="raw/hr-policies/")
    NOISE_GCS_PREFIX: str = Field(default="raw/other-data/")
    PROCESSED_HR_PREFIX: str = Field(default="processed/hr-policies/")
    PROCESSED_NOISE_PREFIX: str = Field(default="processed/other-data/")

    # 3. Embeddings (Jina / FastEmbed)
    JINA_API_KEY: str = Field(default="")
    EMBEDDING_MODEL_NAME: str = Field(default="jina-embeddings-v2-base-en")
    RERANKER_MODEL_NAME: str = Field(default="jina-reranker-v2-base-multilingual")

    # 4. Vector Database (Qdrant Cloud)
    QDRANT_URL: str = Field(default="https://0c4dcb16-fe28-4eca-bfbf-86fc6217460c.us-central1-0.gcp.cloud.qdrant.io")
    QDRANT_API_KEY: str = Field(default="")
    QDRANT_COLLECTION_NAME: str = Field(default="hr_policies")
    QDRANT_NOISY_COLLECTION_NAME: str = Field(default="hr_policies_noisy_demo")

    # 5. LLM Providers & Routing
    GEMINI_API_KEY: str = Field(default="")
    LLM_MODEL_NAME: str = Field(default="gemini-3.5-flash-lite")
    FALLBACK_MODEL_NAME: str = Field(default="openai/gpt-oss-20b")
    GROQ_API_KEY: str = Field(default="")
    GROQ_BASE_URL: str = Field(default="https://api.groq.com/openai/v1")
    JUDGE_MODEL_NAME: str = Field(default="openai/gpt-oss-120b")

    # 6. Chunking & Retrieval Parameters
    CHUNK_SIZE: int = Field(default=500, ge=50, le=5000)
    CHUNK_OVERLAP: int = Field(default=60, ge=0, le=1000)
    TOP_K_RESULTS: int = Field(default=5, ge=1, le=50)
    RERANK_CANDIDATE_K: int = Field(default=12, ge=1, le=100)
    RELEVANCE_THRESHOLD: float = Field(default=0.35, ge=0.0, le=1.0)
    HR_POLICY_CATEGORIES: Set[str] = {
        "Leave", "Work From Home", "Probation", "Notice Period", "Reimbursement",
        "Code of Conduct", "Holidays", "Maternity Paternity", "Travel Expense", "Exit Process",
    }

    # 7. Reliability — Safety Guardrails
    GUARDRAIL_PROVIDER: str = Field(default="gemini_lite")
    GUARDRAIL_OUTPUT_PROVIDER: str = Field(default="local")
    GUARDRAIL_FAIL_OPEN_INPUT: bool = Field(default=False)
    GUARDRAIL_FAIL_OPEN_OUTPUT: bool = Field(default=True)
    GUARDRAIL_HISTORY_TURNS: int = Field(default=6, ge=1, le=20)

    # 8. Reliability — Semantic Cache
    SEMANTIC_CACHE_THRESHOLD: float = Field(default=0.80, ge=0.5, le=1.0)
    SEMANTIC_CACHE_MAX_ENTRIES: int = Field(default=500, ge=10)
    SEMANTIC_CACHE_TTL_SECONDS: int = Field(default=3600, ge=60)

    # 9. Observability & Tracing (LangSmith)
    LANGSMITH_TRACING: str = Field(default="false")
    LANGSMITH_ENDPOINT: str = Field(default="https://api.smith.langchain.com")
    LANGSMITH_API_KEY: str = Field(default="")
    LANGSMITH_PROJECT: str = Field(default="hr-policy-assistant")

    # 10. Access Control & OAuth Whitelist
    ALLOWED_EMPLOYEE_EMAILS: Union[str, List[str]] = Field(default="mentordivesh@gmail.com")

    @field_validator("ALLOWED_EMPLOYEE_EMAILS", mode="after")
    @classmethod
    def parse_allowed_emails(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [email.strip().lower() for email in value.split(",") if email.strip()]
        return [str(e).strip().lower() for e in value if str(e).strip()]

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH) if _ENV_PATH and _ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def check_api_keys(self) -> None:
        """Validate that mandatory vector database and LLM endpoints are configured."""
        required_configs: List[Tuple[str, str]] = [
            ("QDRANT_URL", self.QDRANT_URL),
            ("QDRANT_API_KEY", self.QDRANT_API_KEY),
            ("GEMINI_API_KEY", self.GEMINI_API_KEY),
        ]
        missing = [name for name, value in required_configs if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
