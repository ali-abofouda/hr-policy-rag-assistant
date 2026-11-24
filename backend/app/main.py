"""backend/app/main.py — Production FastAPI Application Server."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging, logger
from backend.app.core.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan manager executing startup and graceful shutdown routines."""
    configure_logging(level=settings.LOG_LEVEL)
    setup_tracing()
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.API_VERSION} in {settings.ENVIRONMENT} environment...")

    try:
        settings.check_api_keys()
        logger.info("API key validation passed.")
    except Exception as exc:
        logger.warning(f"Configuration validation warning: {exc}")

    yield

    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description="Hexagonal Architecture HR Policy Assistant RAG REST API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
