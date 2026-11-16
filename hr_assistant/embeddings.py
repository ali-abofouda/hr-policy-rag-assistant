"""07 · embeddings — Turn text into dense vectors using Jina or local HuggingFace.

Default provider: Jina Embeddings API via JINA_API_KEY and EMBEDDING_MODEL_NAME.
Fallback provider: Local sentence-transformers/all-MiniLM-L6-v2 if Jina API key
is missing or unavailable, ensuring offline zero-cost execution.
"""

import logging
from typing import Any
from langchain_core.embeddings import Embeddings

from hr_assistant import config

logger = logging.getLogger(__name__)


def get_embeddings_model() -> Embeddings:
    """Return an embeddings model instance configured from environment settings.

    Attempts to initialize JinaEmbeddings using config.JINA_API_KEY.
    If JINA_API_KEY is not configured or fails, falls back gracefully to
    local sentence-transformers/all-MiniLM-L6-v2 for reliable offline execution.

    Returns:
        Embeddings instance implementing LangChain Embeddings interface.
    """
    if config.JINA_API_KEY and config.JINA_API_KEY.strip():
        try:
            from langchain_community.embeddings import JinaEmbeddings

            logger.info("Initializing Jina embeddings model: %s", config.EMBEDDING_MODEL_NAME)
            return JinaEmbeddings(
                jina_api_key=config.JINA_API_KEY,
                model_name=config.EMBEDDING_MODEL_NAME,
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize JinaEmbeddings (%s). Falling back to local HuggingFace embeddings.",
                exc,
            )

    logger.info("Using local HuggingFaceEmbeddings (sentence-transformers/all-MiniLM-L6-v2)")
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
