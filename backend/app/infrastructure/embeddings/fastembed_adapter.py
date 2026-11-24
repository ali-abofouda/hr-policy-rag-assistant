"""backend/app/infrastructure/embeddings/fastembed_adapter.py — FastEmbed / Jina Adapter."""

import logging
import warnings
from typing import List
from langchain_core.embeddings import Embeddings

from backend.app.core.config import settings
from backend.app.domain.ports.embedding import EmbeddingPort

logger = logging.getLogger(__name__)


class EmbeddingAdapter(EmbeddingPort):
    """Adapter delivering 768-dimensional embeddings via local FastEmbed or Jina Cloud."""

    def __init__(self):
        self._model: Embeddings = self._build_model()

    def _build_model(self) -> Embeddings:
        if settings.JINA_API_KEY and settings.JINA_API_KEY.strip():
            try:
                from langchain_community.embeddings import JinaEmbeddings
                logger.info("Initializing Jina cloud embeddings model: %s", settings.EMBEDDING_MODEL_NAME)
                return JinaEmbeddings(
                    jina_api_key=settings.JINA_API_KEY,
                    model_name=settings.EMBEDDING_MODEL_NAME,
                )
            except Exception as exc:
                logger.warning("Failed Jina cloud API (%s). Falling back to local FastEmbed.", exc)

        logger.info("Using local FastEmbed embeddings (jinaai/jina-embeddings-v2-base-en, 768-dim) via ONNX")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
            return FastEmbedEmbeddings(model_name="jinaai/jina-embeddings-v2-base-en")

    @property
    def dimension(self) -> int:
        return 768

    def get_embeddings_model(self) -> Embeddings:
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._model.embed_query(text)
