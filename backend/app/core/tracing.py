"""backend/app/core/tracing.py — Observability with LangSmith."""

import os
from loguru import logger
from backend.app.core.config import settings


def setup_tracing() -> None:
    """Initialize LangSmith distributed tracing."""
    if settings.LANGSMITH_TRACING.lower() == "true":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        logger.info(
            f"LangSmith tracing ENABLED - project '{settings.LANGSMITH_PROJECT}', "
            f"traces at https://smith.langchain.com"
        )
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.debug("LangSmith tracing disabled.")
