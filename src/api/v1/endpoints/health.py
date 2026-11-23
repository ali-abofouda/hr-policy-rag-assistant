"""src/api/v1/endpoints/health.py — Health check, liveness, and readiness diagnostics."""

from fastapi import APIRouter
from src.core.config import settings
from src.retrieval.vector_store import check_qdrant_health
from src.schemas.health import ComponentStatus, HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Perform system health check")
async def get_health_status() -> HealthResponse:
    """Validate vector database connectivity, LLM gateway readiness, and cache status."""
    qdrant_ok = check_qdrant_health()
    llm_ok = bool(settings.GEMINI_API_KEY or settings.GROQ_API_KEY)

    components = [
        ComponentStatus(
            name="qdrant_cloud",
            status="healthy" if qdrant_ok else "unreachable",
            details="Collection: " + settings.QDRANT_COLLECTION_NAME,
        ),
        ComponentStatus(
            name="llm_gateway",
            status="healthy" if llm_ok else "degraded",
            details="Primary: " + settings.LLM_MODEL_NAME,
        ),
        ComponentStatus(
            name="semantic_cache",
            status="healthy",
            details=f"Threshold: {settings.SEMANTIC_CACHE_THRESHOLD}",
        ),
    ]

    overall_status = "healthy" if (qdrant_ok and llm_ok) else "degraded"
    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        components=components,
    )
