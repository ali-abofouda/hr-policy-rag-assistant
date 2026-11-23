"""17 · pipeline — Wire components into ready-to-use agents and execute the ask() flow.

Secure Pipeline Flow:
  input_guardrail (13) -> semantic_cache (14) -> agent (16) -> output_guardrail (13) -> cache store.

Functions:
  build_hr_assistant: Returns (agent, cache) against standard 'hr_policies' collection.
  build_reliability_assistant: Returns (agent, cache) against noisy collection for red-teaming.
  build_plain_assistant: Baseline assistant with no guardrails or cache for comparison.
  ask: Full secure flow with screening, caching, and persistent conversational memory.
  ask_plain: Raw agent call without safety guardrails or cache.
"""

import logging
from typing import Any, Optional, Tuple, Union

from langgraph.checkpoint.memory import InMemorySaver

from hr_assistant import config, thread_memory
from hr_assistant.agent import create_hr_agent, create_reliability_agent
from hr_assistant.guardrails import check_input, check_output
from hr_assistant.llm import get_llm
from hr_assistant.semantic_cache import SemanticCache
from hr_assistant.tools import create_guarded_search_tool, create_search_tool
from hr_assistant.vector_store import collection_exists, load_vector_store

logger = logging.getLogger(__name__)

INPUT_BLOCKED_MESSAGE: str = "I can't process that request — it was flagged by the input safety guardrail."
OUTPUT_BLOCKED_MESSAGE: str = "I can't share that answer as generated — it was flagged by the output safety guardrail."

# Shared module-level cache fallback for callers invoking ask(agent, question) without passing cache
_DEFAULT_CACHE: Optional[SemanticCache] = None


def _get_default_cache() -> SemanticCache:
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        _DEFAULT_CACHE = SemanticCache()
    return _DEFAULT_CACHE


def _bootstrap_collection(collection_name: str, ingest_fn) -> None:
    """First-run convenience: if the Qdrant collection isn't there yet,
    run ingestion once locally. After that this is a no-op."""
    if collection_exists(collection_name):
        return

    logger.info("Collection '%s' not found — running first-time local ingestion.", collection_name)
    ingest_fn()


def _resolve_checkpointer(checkpointer: Optional[Any]) -> Optional[Any]:
    """Resolve checkpointer: None defaults to InMemorySaver, False to None for LangGraph Studio."""
    if checkpointer is None:
        return InMemorySaver()
    if checkpointer is False:
        return None
    return checkpointer


def _build_guarded_assistant(collection_name: str, ingest_fn, checkpointer: Optional[Any] = None) -> Tuple[Any, SemanticCache]:
    """Assemble the secure stack: guarded search tool + RELIABILITY_SYSTEM_PROMPT + memory + semantic cache."""
    config.check_api_keys()
    _bootstrap_collection(collection_name, ingest_fn)

    vector_store = load_vector_store(collection_name)
    agent = create_reliability_agent(
        llm=get_llm(),
        tools=[create_guarded_search_tool(vector_store)],
        checkpointer=_resolve_checkpointer(checkpointer),
    )
    return agent, SemanticCache()


def build_hr_assistant(checkpointer: Optional[Any] = None) -> Tuple[Any, SemanticCache]:
    """Build the production guarded HR assistant against the clean hr_policies collection.

    Returns:
        Tuple of (agent, cache) ready to be driven by ask().
    """
    from hr_assistant.ingestion import ingest_hr_policies

    return _build_guarded_assistant(
        config.QDRANT_COLLECTION_NAME,
        ingest_hr_policies,
        checkpointer=checkpointer,
    )


def build_reliability_assistant(checkpointer: Optional[Any] = None) -> Tuple[Any, SemanticCache]:
    """Build the guarded assistant against the mixed HR + noisy collection for stress-testing.

    Returns:
        Tuple of (agent, cache).
    """
    from hr_assistant.ingestion import ingest_noisy_corpus

    return _build_guarded_assistant(
        config.QDRANT_NOISY_COLLECTION_NAME,
        ingest_noisy_corpus,
        checkpointer=checkpointer,
    )


def build_plain_assistant(checkpointer: Optional[Any] = None) -> Any:
    """Build unguarded baseline assistant for red-team comparisons.

    Wires plain search tool and plain SYSTEM_PROMPT without safety guardrails or cache.
    """
    from hr_assistant.ingestion import ingest_hr_policies

    config.check_api_keys()
    _bootstrap_collection(config.QDRANT_COLLECTION_NAME, ingest_hr_policies)

    vector_store = load_vector_store(config.QDRANT_COLLECTION_NAME)
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
    """Execute full secure turn:
    input safety guardrail (current turn + history) -> semantic cache -> agent -> output safety guardrail -> cache store.

    Supports both signatures:
      - ask(agent, cache, question, thread_id=...) [Standard Phase 2 signature]
      - ask(agent, question, thread_id=...)        [Backward-compatible signature]

    Args:
        agent: Compiled LangGraph agent.
        cache_or_question: SemanticCache instance OR question string.
        question_or_none: Question string if cache was passed as 2nd arg.
        thread_id: Session identifier for conversational memory.

    Returns:
        Grounded answer string or safety block message.
    """
    if isinstance(cache_or_question, SemanticCache):
        cache: SemanticCache = cache_or_question
        question: str = str(question_or_none)
    else:
        cache: SemanticCache = _get_default_cache()
        question: str = str(cache_or_question)

    # 1. Screen input against guardrail using current query + recent conversation turns
    screen_text = thread_memory.input_text_for_screening(agent, question, thread_id)
    input_ok, input_reason = check_input(screen_text)
    logger.info("INPUT GUARDRAIL: %s (%s)", "PASS" if input_ok else "BLOCK", input_reason)
    if not input_ok:
        # Deliberately not recorded in memory to keep hostile prompt out of model context
        return INPUT_BLOCKED_MESSAGE

    # 2. Check semantic cache for near-duplicate question
    cached_answer = cache.lookup(question)
    if cached_answer is not None:
        # Record turn in thread memory so follow-up queries retain conversation continuity
        thread_memory.record_turn(agent, thread_id, question, cached_answer)
        return cached_answer

    # 3. Invoke agent through thread memory
    message = thread_memory.invoke_agent(agent, question, thread_id)
    answer = getattr(message, "text", None) or str(getattr(message, "content", ""))

    # 4. Screen output against guardrail before writing to cache or returning to user
    output_ok, output_reason = check_output(answer)
    logger.info("OUTPUT GUARDRAIL: %s (%s)", "PASS" if output_ok else "BLOCK", output_reason)
    if not output_ok:
        thread_memory.overwrite_answer(agent, thread_id, message, OUTPUT_BLOCKED_MESSAGE)
        return OUTPUT_BLOCKED_MESSAGE

    # 5. Store verified answer in semantic cache for future instant hits
    cache.store(question, answer)
    return answer


# Backward compatibility alias
ask_reliably = ask
