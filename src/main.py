"""src/main.py — Production FastAPI Application for HR Policy Assistant."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.endpoints.health import router as health_router
from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: initialize subsystems on startup and clean up on shutdown."""
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info("Starting %s v%s in %s environment", settings.PROJECT_NAME, settings.API_VERSION, settings.ENVIRONMENT)

    # Validate essential configuration
    try:
        settings.check_api_keys()
        logger.info("API key validation passed.")
    except Exception as exc:
        logger.warning("Configuration notice during startup: %s", exc)

    yield

    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description="Production RAG system for HR policy question answering with semantic caching, guardrails, and hybrid retrieval.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Top-level health probe for Kubernetes/Docker container healthchecks
    app.include_router(health_router, prefix="", tags=["Health"])

    # Versioned API routes (/api/v1/chat, /api/v1/health)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, str]:
        """Root service metadata."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.API_VERSION,
            "status": "operational",
            "docs": "/docs",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
