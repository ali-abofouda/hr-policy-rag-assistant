"""Unit tests validating the Hexagonal Architecture (Ports, Adapters, Composition Root, and REST API)."""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

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
from backend.app.domain.models.chat import ChatResponse
from backend.app.dependencies import get_chat_service, get_settings
from backend.app.main import app


class TestHexagonalArchitecture(unittest.TestCase):
    """Validate Ports & Adapters contracts, dependency injection, and REST endpoints."""

    def test_ports_and_adapters_contracts(self):
        """Verify all infrastructure adapters implement their corresponding domain protocols."""
        llm = LiteLLMAdapter()
        self.assertIsInstance(llm, LLMPort)

        embeddings = EmbeddingAdapter()
        self.assertIsInstance(embeddings, EmbeddingPort)

        vector_store = QdrantAdapter()
        self.assertIsInstance(vector_store, VectorStorePort)

        reranker = RerankerAdapter()
        self.assertIsInstance(reranker, RerankerPort)

        cache = SemanticCacheAdapter()
        self.assertIsInstance(cache, CachePort)

        guardrail = GuardrailService()
        self.assertIsInstance(guardrail, GuardrailPort)

    def test_composition_root_dependencies(self):
        """Verify composition root correctly initializes and wires domain singletons."""
        settings = get_settings()
        self.assertIsNotNone(settings)
        self.assertEqual(settings.PROJECT_NAME, "HR Policy Assistant RAG")

    def test_backend_api_health_endpoint(self):
        """Verify backend FastAPI /health endpoint returns 200 OK and valid schema."""
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("vector_store", data["components"])

    def test_backend_api_chat_endpoint_mocked(self):
        """Verify backend /api/v1/chat endpoint delegates to ChatService via dependency injection."""
        client = TestClient(app)
        mock_chat_service = MagicMock(spec=ChatService)
        mock_chat_service.ask.return_value = ChatResponse(
            answer="You are entitled to 18 days of paid annual leave.",
            thread_id="test-session-hex",
            is_cached=False,
            latency_seconds=0.12,
        )

        app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
        try:
            response = client.post(
                "/api/v1/chat",
                json={"query": "How many days of annual leave do I get?", "thread_id": "test-session-hex"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["answer"], "You are entitled to 18 days of paid annual leave.")
            self.assertEqual(data["thread_id"], "test-session-hex")
            self.assertFalse(data["is_cached"])
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
