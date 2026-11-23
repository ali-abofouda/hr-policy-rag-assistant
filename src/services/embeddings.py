"""07 · embeddings — Turn text into dense vectors using Jina Cloud or local FastEmbed.

Default provider: Jina Embeddings API via JINA_API_KEY and EMBEDDING_MODEL_NAME.
Fallback / Local provider: Local FastEmbed (jinaai/jina-embeddings-v2-base-en) via ONNX Runtime,
delivering 768-dimensional vectors 100% offline with zero cost and no API keys required.
"""

import logging
import warnings
from typing import Any
from langchain_core.embeddings import Embeddings

from hr_assistant import config

logger = logging.getLogger(__name__)


def get_embeddings_model() -> Embeddings:
    """Return an embeddings model instance configured from environment settings.

    Attempts to initialize JinaEmbeddings using config.JINA_API_KEY.
    If JINA_API_KEY is not configured or unavailable, falls back gracefully to
    local FastEmbed (jinaai/jina-embeddings-v2-base-en) for reliable, zero-cost
    768-dimensional vector computation via ONNX Runtime.

    Returns:
        Embeddings instance implementing LangChain Embeddings interface.
    """
    if config.JINA_API_KEY and config.JINA_API_KEY.strip():
        try:
            from langchain_community.embeddings import JinaEmbeddings

            logger.info("Initializing Jina cloud embeddings model: %s", config.EMBEDDING_MODEL_NAME)
            return JinaEmbeddings(
                jina_api_key=config.JINA_API_KEY,
                model_name=config.EMBEDDING_MODEL_NAME,
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize JinaEmbeddings cloud API (%s). Falling back to local FastEmbed.",
                exc,
            )

    logger.info("Using local FastEmbed embeddings (jinaai/jina-embeddings-v2-base-en, 768-dim) via ONNX Runtime")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        return FastEmbedEmbeddings(
            model_name="jinaai/jina-embeddings-v2-base-en"
        )

