"""tests/test_api.py — Unit and integration tests for FastAPI endpoints."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.api.deps import get_assistant
from src.main import app
from src.schemas.chat import ChatResponse
from src.schemas.health import HealthResponse


class TestFastAPIEndpoints(unittest.TestCase):
    """Test suite for root, health diagnostics, and chat endpoints."""

    def setUp(self) -> None:
        """Initialize TestClient and mock assistant bundle."""
        self.client = TestClient(app)

        # Mock agent and semantic cache
        self.mock_agent = MagicMock()
        self.mock_cache = MagicMock()
        self.mock_cache.lookup.return_value = None

        # Set default mock dependency override
        app.dependency_overrides[get_assistant] = lambda: (self.mock_agent, self.mock_cache)

    def tearDown(self) -> None:
        """Reset dependency overrides after each test."""
        app.dependency_overrides.clear()

    def test_root_endpoint(self) -> None:
        """Test GET / returns operational metadata."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("name", data)
        self.assertIn("version", data)
        self.assertEqual(data["status"], "operational")

    @patch("src.api.v1.endpoints.health.check_qdrant_health", return_value=True)
    def test_health_endpoint(self, mock_qdrant: MagicMock) -> None:
        """Test GET /health returns structured health diagnostics."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validate with Pydantic model
        health_obj = HealthResponse.model_validate(data)
        self.assertIn(health_obj.status, ("healthy", "degraded"))
        self.assertEqual(len(health_obj.components), 3)

        component_names = {c.name for c in health_obj.components}
        self.assertIn("qdrant_cloud", component_names)
        self.assertIn("llm_gateway", component_names)
        self.assertIn("semantic_cache", component_names)

    @patch("src.api.v1.endpoints.chat.ask")
    def test_chat_endpoint_success(self, mock_ask: MagicMock) -> None:
        """Test POST /api/v1/chat processes a valid query and extracts citations."""
        mock_ask.return_value = (
            "You are entitled to 18 days of annual leave. (Source: leave_policy.txt)"
        )

        payload = {
            "query": "How many days of annual leave do I get?",
            "thread_id": "test-thread-001",
        }
        response = self.client.post("/api/v1/chat", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        chat_resp = ChatResponse.model_validate(data)

        self.assertEqual(chat_resp.thread_id, "test-thread-001")
        self.assertIn("18 days", chat_resp.answer)
        self.assertFalse(chat_resp.is_cached)
        self.assertGreaterEqual(chat_resp.latency_seconds, 0.0)
        self.assertEqual(len(chat_resp.citations), 1)
        self.assertEqual(chat_resp.citations[0].source, "leave_policy.txt")

    @patch("src.api.v1.endpoints.chat.ask")
    def test_chat_endpoint_cache_hit(self, mock_ask: MagicMock) -> None:
        """Test POST /api/v1/chat marks response as cached when cache lookup succeeds."""
        self.mock_cache.lookup.return_value = "Cached answer from policy. (Source: policy.txt)"
        mock_ask.return_value = "Cached answer from policy. (Source: policy.txt)"

        payload = {"query": "How many days leave?"}
        response = self.client.post("/api/v1/chat", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        chat_resp = ChatResponse.model_validate(data)
        self.assertTrue(chat_resp.is_cached)

    def test_chat_endpoint_validation_error(self) -> None:
        """Test POST /api/v1/chat with invalid empty body returns 422."""
        response = self.client.post("/api/v1/chat", json={"query": ""})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
