"""Unit tests for LLM Gateway, Router initialization, and failover mechanism."""

import unittest
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router

from hr_assistant import config
from hr_assistant.llm import _get_router, get_llm


class TestLLMGateway(unittest.TestCase):
    """Test LiteLLM Gateway Router configuration and execution."""

    def test_router_configuration(self):
        """Verify that _get_router creates a valid Router with primary and fallback models."""
        router = _get_router()
        self.assertIsInstance(router, Router)
        self.assertEqual(router.num_retries, 2)

        # Verify model group names
        model_names = [m.get("model_name") for m in router.model_list]
        self.assertIn("hr-llm", model_names)

        if config.GROQ_API_KEY:
            self.assertIn("hr-llm-fallback", model_names)
            self.assertTrue(len(router.fallbacks) > 0)
            self.assertIn("hr-llm", router.fallbacks[0])

    def test_get_llm_structure(self):
        """Verify that get_llm returns a ChatLiteLLMRouter instance with temperature 0."""
        llm = get_llm()
        self.assertIsInstance(llm, ChatLiteLLMRouter)
        self.assertEqual(llm.model_name, "hr-llm")
        self.assertEqual(llm.temperature, 0.0)

    def test_router_fallback_resolution(self):
        """Verify that fallback routing maps primary failures to the fallback group."""
        router = _get_router()
        if config.GROQ_API_KEY:
            self.assertTrue(len(router.fallbacks) > 0)
            self.assertEqual(router.fallbacks[0].get("hr-llm"), ["hr-llm-fallback"])
