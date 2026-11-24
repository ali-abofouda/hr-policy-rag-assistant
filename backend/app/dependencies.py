"""backend/app/dependencies.py — Composition Root / Dependency Injection Wiring.

This module acts as the single composition root for the application, instantiating
concrete infrastructure adapters and wiring them into domain services.
"""

from functools import lru_cache
from typing import Optional

from backend.app.core.config import Settings, settings
from backend.app.domain.ports.llm import LLMPort
from backend.app.domain.ports.embedding import EmbeddingPort
from backend.app.domain.ports.vector_store import VectorStorePort
from backend.app.domain.ports.reranker import RerankerPort
from backend.app.domain.ports.cache import CachePort
from backend.app.domain.ports.guardrail import GuardrailPort

from backend.app.infrastructure.llms.litellm_adapter import LiteLLMAdapter
from backend.app.infrastructure.embeddings.fastembed_adapter import EmbeddingAdapter
from backend.app.infrastructure.vectorstore.qdrant_adapter import QdrantAdapter
from backend.app.infrastructure.rerankers.cross_encoder_adapter import RerankerAdapter
from backend.app.infrastructure.cache.semantic_cache_adapter import SemanticCacheAdapter
from backend.app.domain.services.guardrail_service import GuardrailService
from backend.app.domain.services.chat_service import ChatService


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return application settings singleton."""
    return settings


@lru_cache(maxsize=1)
def get_llm_adapter() -> LLMPort:
    """Return LLM Gateway adapter singleton."""
    return LiteLLMAdapter()


@lru_cache(maxsize=1)
def get_embedding_adapter() -> EmbeddingPort:
    """Return embedding provider adapter singleton."""
    return EmbeddingAdapter()


@lru_cache(maxsize=1)
def get_vector_store_adapter() -> VectorStorePort:
    """Return Qdrant vector store adapter singleton."""
    return QdrantAdapter()


@lru_cache(maxsize=1)
def get_reranker_adapter() -> RerankerPort:
    """Return cross-encoder reranker adapter singleton."""
    return RerankerAdapter()


@lru_cache(maxsize=1)
def get_cache_adapter() -> CachePort:
    """Return semantic cache adapter singleton."""
    return SemanticCacheAdapter()


@lru_cache(maxsize=1)
def get_guardrail_service() -> GuardrailPort:
    """Return safety guardrail screening service singleton."""
    return GuardrailService()


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    """Return wired Domain ChatService singleton."""
    return ChatService(
        llm=get_llm_adapter(),
        vector_store=get_vector_store_adapter(),
        reranker=get_reranker_adapter(),
        cache=get_cache_adapter(),
        guardrail=get_guardrail_service(),
    )
