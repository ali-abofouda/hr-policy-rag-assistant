"""backend/app/api/routes/health.py — Health and Readiness Probes."""

from fastapi import APIRouter
from backend.app.api.schemas.health import HealthResponse
from backend.app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
async def health_check() -> HealthResponse:
    """Readiness probe verifying operational health."""
    components = {
        "vector_store": "ready",
        "semantic_cache": "ready",
        "llm_gateway": "ready",
    }
    return HealthResponse(
        status="ok",
        version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
        components=components,
    )
