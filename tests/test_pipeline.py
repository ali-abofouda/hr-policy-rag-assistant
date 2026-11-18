"""Unit tests for tracing and pipeline execution."""

import unittest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

from hr_assistant.tracing import check_langsmith_tracing
from hr_assistant.pipeline import ask


class TestTracingAndPipeline(unittest.TestCase):
    """Test tracing logger and pipeline ask function."""

    def test_check_langsmith_tracing_runs(self):
        """Verify check_langsmith_tracing runs without throwing any exception."""
        try:
            check_langsmith_tracing()
        except Exception as e:
            self.fail(f"check_langsmith_tracing raised {e}")

    def test_ask_extracts_text_properly(self):
        """Verify ask method safely extracts text from agent response."""
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                AIMessage(content="Annual leave is 18 days.")
            ]
        }

        answer = ask(mock_agent, "How many annual leaves?", thread_id="test-session")
        self.assertIn("18 days", answer)
        mock_agent.invoke.assert_called_once()
