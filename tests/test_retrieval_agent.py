"""Unit tests for the retrieval pipeline components (reranker, tools, and agent)."""

import unittest
from unittest.mock import MagicMock
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.retrieval.reranker import rerank
from src.agent.tools import create_search_tool
from src.agent.agent import create_hr_agent


class TestRetrievalPipeline(unittest.TestCase):
    """Test reranker, tools, and agent creation."""

    def test_reranker_handles_empty_candidates(self):
        """Verify that rerank returns empty list on empty candidates or top_n <= 0."""
        self.assertEqual(rerank("query", []), [])
        self.assertEqual(rerank("query", [], top_n=0), [])
        docs = [Document(page_content="test doc")]
        self.assertEqual(rerank("query", docs, top_n=0), [])

    def test_local_semantic_rerank_slices_top_n(self):
        """Verify that local rerank returns top_n candidates."""
        candidates = [
            Document(page_content="Annual leave policy allows 30 days of paid vacation per calendar year.", metadata={"source": "leave.txt"}),
            Document(page_content="Notice period is 60 calendar days upon employee resignation.", metadata={"source": "notice.txt"}),
            Document(page_content="Q3 quarterly revenue and financial sales metrics summary.", metadata={"source": "sales.txt"}),
        ]

        # Query specifically about leave
        ranked = rerank("How many annual leave days do I get?", candidates, top_n=2)
        self.assertEqual(len(ranked), 2)

    def test_create_search_tool_structure(self):
        """Verify that create_search_tool creates a valid LangChain tool."""
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = [
            Document(page_content="Leave policy content", metadata={"source": "leave_policy.txt"})
        ]

        # Patch get_retriever inside tools
        tool = create_search_tool(mock_vector_store)
        self.assertEqual(tool.name, "search_hr_policy")
        self.assertIn("leave", tool.description.lower())
        self.assertIn("probation", tool.description.lower())

    def test_create_hr_agent_compilation(self):
        """Verify that create_hr_agent compiles a state graph with tools and memory."""
        from langchain_core.tools import tool

        @tool
        def dummy_search_tool(question: str) -> str:
            """Dummy search tool for testing agent compilation."""
            return "dummy result"

        fake_llm = FakeMessagesListChatModel(responses=[AIMessage(content="Hello")])
        checkpointer = MemorySaver()
        agent = create_hr_agent(
            llm=fake_llm,
            tools=[dummy_search_tool],
            checkpointer=checkpointer,
        )
        self.assertIsNotNone(agent)
        # Check that it is a compiled graph
        self.assertTrue(hasattr(agent, "invoke"))


if __name__ == "__main__":
    unittest.main()
