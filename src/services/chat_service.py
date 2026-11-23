"""src/services/chat_service.py — Enterprise Application Service coordinating RAG turn execution.

Coordinates:
  input_guardrail (security) -> semantic_cache (security) -> agent (agent) -> output_guardrail (security) -> cache store.
"""

import logging
from typing import Any, Optional, Tuple, Union

from langgraph.checkpoint.memory import InMemorySaver

from src.core.config import settings
from src.agent.agent import create_hr_agent, create_reliability_agent
from src.agent.llm import get_llm
from src.agent.tools import create_guarded_search_tool, create_search_tool
from src.agent import thread_memory
from src.ingestion.ingestion import ingest_hr_policies, ingest_noisy_corpus
from src.retrieval.vector_store import collection_exists, load_vector_store
from src.security.guardrails import check_input, check_output
from src.security.semantic_cache import SemanticCache

logger = logging.getLogger(__name__)

INPUT_BLOCKED_MESSAGE: str = "I can't process that request — it was flagged by the input safety guardrail."
OUTPUT_BLOCKED_MESSAGE: str = "I can't share that answer as generated — it was flagged by the output safety guardrail."

# Shared default cache fallback
_DEFAULT_CACHE: Optional[SemanticCache] = None


def _get_default_cache() -> SemanticCache:
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        _DEFAULT_CACHE = SemanticCache()
    return _DEFAULT_CACHE


def _bootstrap_collection(collection_name: str, ingest_fn: Any) -> None:
    """Ensure collection exists in Qdrant Cloud or initialize on first run."""
    if collection_exists(collection_name):
        return
    logger.info("Collection '%s' not found — running first-time ingestion.", collection_name)
    ingest_fn()


def _resolve_checkpointer(checkpointer: Optional[Any]) -> Optional[Any]:
    if checkpointer is None:
        return InMemorySaver()
    if checkpointer is False:
        return None
    return checkpointer


def _build_guarded_assistant(collection_name: str, ingest_fn: Any, checkpointer: Optional[Any] = None) -> Tuple[Any, SemanticCache]:
    settings.check_api_keys()
    _bootstrap_collection(collection_name, ingest_fn)

    vector_store = load_vector_store(collection_name)
    agent = create_reliability_agent(
        llm=get_llm(),
        tools=[create_guarded_search_tool(vector_store)],
        checkpointer=_resolve_checkpointer(checkpointer),
    )
    return agent, SemanticCache()


def build_hr_assistant(checkpointer: Optional[Any] = None) -> Tuple[Any, SemanticCache]:
    """Build production guarded HR assistant against clean hr_policies collection."""
    return _build_guarded_assistant(
        settings.QDRANT_COLLECTION_NAME,
        ingest_hr_policies,
        checkpointer=checkpointer,
    )


def build_reliability_assistant(checkpointer: Optional[Any] = None) -> Tuple[Any, SemanticCache]:
    """Build guarded assistant against mixed HR + noisy collection for stress-testing."""
    return _build_guarded_assistant(
        settings.QDRANT_NOISY_COLLECTION_NAME,
        ingest_noisy_corpus,
        checkpointer=checkpointer,
    )


def build_plain_assistant(checkpointer: Optional[Any] = None) -> Any:
    """Build unguarded baseline assistant for red-team comparisons."""
    settings.check_api_keys()
    _bootstrap_collection(settings.QDRANT_COLLECTION_NAME, ingest_hr_policies)

    vector_store = load_vector_store(settings.QDRANT_COLLECTION_NAME)
    plain_tool = create_search_tool(vector_store)

    return create_hr_agent(
        llm=get_llm(),
        tools=[plain_tool],
        checkpointer=_resolve_checkpointer(checkpointer),
    )


def ask_plain(agent: Any, question: str, thread_id: str = "default-session") -> str:
    """Raw agent invocation without safety guardrails or semantic cache."""
    return thread_memory.invoke_agent(agent, question, thread_id).text


def ask(
    agent: Any,
    cache_or_question: Union[SemanticCache, str],
    question_or_none: Optional[str] = None,
    thread_id: str = "default-session",
) -> str:
    """Execute secure RAG turn:
    input guardrail -> semantic cache -> agent -> output guardrail -> cache store.
    """
    if isinstance(cache_or_question, SemanticCache):
        cache: SemanticCache = cache_or_question
        question: str = str(question_or_none)
    else:
        cache: SemanticCache = _get_default_cache()
        question: str = str(cache_or_question)

    # 1. Screen input against guardrail
    screen_text = thread_memory.input_text_for_screening(agent, question, thread_id)
    input_ok, input_reason = check_input(screen_text)
    logger.info("INPUT GUARDRAIL: %s (%s)", "PASS" if input_ok else "BLOCK", input_reason)
    if not input_ok:
        return INPUT_BLOCKED_MESSAGE

    # 2. Check semantic cache
    cached_answer = cache.lookup(question)
    if cached_answer is not None:
        thread_memory.record_turn(agent, thread_id, question, cached_answer)
        return cached_answer

    # 3. Invoke agent through conversational thread memory
    message = thread_memory.invoke_agent(agent, question, thread_id)
    answer = getattr(message, "text", None) or str(getattr(message, "content", ""))

    # 4. Screen output against guardrail
    output_ok, output_reason = check_output(answer)
    logger.info("OUTPUT GUARDRAIL: %s (%s)", "PASS" if output_ok else "BLOCK", output_reason)
    if not output_ok:
        thread_memory.overwrite_answer(agent, thread_id, message, OUTPUT_BLOCKED_MESSAGE)
        return OUTPUT_BLOCKED_MESSAGE

    # 5. Store verified answer in semantic cache
    cache.store(question, answer)
    return answer


ask_reliably = ask
