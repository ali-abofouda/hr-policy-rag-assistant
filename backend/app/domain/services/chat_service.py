"""backend/app/domain/services/chat_service.py — Hexagonal Domain Chat Service."""

import logging
import time
from typing import Any, List, Optional, Tuple, Union

from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from backend.app.core.config import settings
from backend.app.domain.models.chat import ChatResponse, Citation, GuardrailResult
from backend.app.domain.ports.llm import LLMPort
from backend.app.domain.ports.vector_store import VectorStorePort
from backend.app.domain.ports.reranker import RerankerPort
from backend.app.domain.ports.cache import CachePort
from backend.app.domain.ports.guardrail import GuardrailPort
from backend.app.domain.services.guardrail_service import GuardrailService
from backend.app.infrastructure.llms.litellm_adapter import LiteLLMAdapter
from backend.app.infrastructure.vectorstore.qdrant_adapter import QdrantAdapter
from backend.app.infrastructure.rerankers.cross_encoder_adapter import RerankerAdapter
from backend.app.infrastructure.cache.semantic_cache_adapter import SemanticCacheAdapter

from src.agent.agent import create_hr_agent, create_reliability_agent
from src.agent.tools import create_guarded_search_tool, create_search_tool
from src.agent import thread_memory
from src.ingestion.ingestion import ingest_hr_policies, ingest_noisy_corpus

logger = logging.getLogger(__name__)

INPUT_BLOCKED_MESSAGE: str = "I can't process that request — it was flagged by the input safety guardrail."
OUTPUT_BLOCKED_MESSAGE: str = "I can't share that answer as generated — it was flagged by the output safety guardrail."


class ChatService:
    """Enterprise domain service executing guarded RAG query workflows with Ports & Adapters."""

    def __init__(
        self,
        llm: Optional[LLMPort] = None,
        vector_store: Optional[VectorStorePort] = None,
        reranker: Optional[RerankerPort] = None,
        cache: Optional[CachePort] = None,
        guardrail: Optional[GuardrailPort] = None,
        checkpointer: Optional[Any] = None,
    ):
        self.llm = llm or LiteLLMAdapter()
        self.vector_store = vector_store or QdrantAdapter()
        self.reranker = reranker or RerankerAdapter()
        self.cache = cache or SemanticCacheAdapter()
        self.guardrail = guardrail or GuardrailService()
        self.checkpointer = InMemorySaver() if checkpointer is None else checkpointer

        # Build underlying LangGraph agent
        raw_vs = getattr(self.vector_store, "get_vector_store", lambda: self.vector_store)()
        guarded_tool = create_guarded_search_tool(raw_vs)
        raw_llm = getattr(self.llm, "get_chat_model", lambda: self.llm)()

        self.agent = create_reliability_agent(
            llm=raw_llm,
            tools=[guarded_tool],
            checkpointer=self.checkpointer,
        )

    def ask(self, question: str, thread_id: str = "default-session") -> ChatResponse:
        """Execute full hexagonal RAG pipeline turn."""
        start_time = time.time()

        # 1. Screen input against guardrail
        screen_text = thread_memory.input_text_for_screening(self.agent, question, thread_id)
        input_ok, input_reason = self.guardrail.evaluate_input(screen_text)
        logger.info("INPUT GUARDRAIL: %s (%s)", "PASS" if input_ok else "BLOCK", input_reason)

        if not input_ok:
            return ChatResponse(
                answer=INPUT_BLOCKED_MESSAGE,
                thread_id=thread_id,
                is_cached=False,
                latency_seconds=round(time.time() - start_time, 3),
                guardrail_status=f"BLOCKED_INPUT: {input_reason}",
            )

        # 2. Check semantic cache
        cached_answer, sim_score, matched_q = self.cache.lookup(question)
        if cached_answer is not None:
            thread_memory.record_turn(self.agent, thread_id, question, cached_answer)
            return ChatResponse(
                answer=cached_answer,
                thread_id=thread_id,
                is_cached=True,
                latency_seconds=round(time.time() - start_time, 3),
                guardrail_status="PASS (CACHED)",
            )

        # 3. Invoke LangGraph agent
        message = thread_memory.invoke_agent(self.agent, question, thread_id)
        answer = getattr(message, "text", None) or str(getattr(message, "content", ""))

        # 4. Screen output against guardrail
        output_ok, output_reason = self.guardrail.evaluate_output(answer)
        logger.info("OUTPUT GUARDRAIL: %s (%s)", "PASS" if output_ok else "BLOCK", output_reason)

        if not output_ok:
            thread_memory.overwrite_answer(self.agent, thread_id, message, OUTPUT_BLOCKED_MESSAGE)
            return ChatResponse(
                answer=OUTPUT_BLOCKED_MESSAGE,
                thread_id=thread_id,
                is_cached=False,
                latency_seconds=round(time.time() - start_time, 3),
                guardrail_status=f"BLOCKED_OUTPUT: {output_reason}",
            )

        # 5. Store verified answer in semantic cache
        self.cache.store(question, answer)

        # 6. Extract source citations
        citations = []
        if "*(Source:" in answer:
            import re
            for m in re.finditer(r"\*\(Source:\s*([^)]+)\)\*", answer):
                src = m.group(1).strip()
                citations.append(Citation(source=src))

        return ChatResponse(
            answer=answer,
            thread_id=thread_id,
            is_cached=False,
            latency_seconds=round(time.time() - start_time, 3),
            citations=citations,
            guardrail_status="PASS",
        )


# Backward-compatible factory and helper functions matching legacy chat_service
def build_hr_assistant(checkpointer: Optional[Any] = None) -> Tuple[Any, Any]:
    from src.services.chat_service import build_hr_assistant as legacy_build
    return legacy_build(checkpointer=checkpointer)


def ask(agent: Any, cache_or_question: Any, question_or_none: Optional[str] = None, thread_id: str = "default-session") -> str:
    from src.services.chat_service import ask as legacy_ask
    return legacy_ask(agent, cache_or_question, question_or_none, thread_id)
