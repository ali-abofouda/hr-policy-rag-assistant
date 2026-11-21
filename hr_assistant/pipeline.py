"""Pipeline module to wire components into guarded and plain assistants with safety checks."""

import logging
from typing import Any, Optional

from langgraph.checkpoint.memory import InMemorySaver

from hr_assistant import config
from hr_assistant.agent import create_hr_agent, create_reliability_agent
from hr_assistant.guardrails import check_input, check_output
from hr_assistant.llm import get_llm
from hr_assistant.tools import create_guarded_search_tool, create_search_tool
from hr_assistant.vector_store import collection_exists, load_vector_store

logger = logging.getLogger(__name__)

INPUT_BLOCKED_MESSAGE: str = "I can't process that request — it was flagged by the input safety guardrail."
OUTPUT_BLOCKED_MESSAGE: str = "I can't share that answer as generated — it was flagged by the output safety guardrail."


def _bootstrap_collection(collection_name: str, ingest_fn) -> None:
    """First-run convenience: if the Qdrant collection isn't there yet,
    run ingestion once locally. After that this is a no-op."""
    if collection_exists(collection_name):
        return

    logger.info("Collection '%s' not found — running first-time local ingestion.", collection_name)
    ingest_fn()


def _resolve_checkpointer(checkpointer: Optional[Any]) -> Optional[Any]:
    """Resolve checkpointer: None defaults to InMemorySaver, False to None."""
    if checkpointer is None:
        return InMemorySaver()
    if checkpointer is False:
        return None
    return checkpointer


def build_hr_assistant(checkpointer: Optional[Any] = None) -> Any:
    """Build the production guarded HR assistant.

    Wires:
    - LLM Gateway (LiteLLM Router with Gemini + Groq fallback).
    - Guarded search tool with category filter and relevance floor.
    - RELIABILITY_SYSTEM_PROMPT with identity lock and noise awareness.
    - Conversational memory checkpointer.

    Returns:
        Compiled LangGraph agent ready to be invoked via ask().
    """
    from hr_assistant.ingestion import ingest_hr_policies

    config.check_api_keys()
    _bootstrap_collection(config.QDRANT_COLLECTION_NAME, ingest_hr_policies)

    vector_store = load_vector_store(config.QDRANT_COLLECTION_NAME)
    guarded_tool = create_guarded_search_tool(vector_store)

    return create_reliability_agent(
        llm=get_llm(),
        tools=[guarded_tool],
        checkpointer=_resolve_checkpointer(checkpointer),
    )


def build_plain_assistant(checkpointer: Optional[Any] = None) -> Any:
    """Build unguarded plain baseline assistant for red-team comparisons.

    Wires plain search tool and plain SYSTEM_PROMPT without safety guardrails.
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
    """Raw agent invocation without safety guardrails or screening."""
    response = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    last_message = response["messages"][-1]

    if hasattr(last_message, "text") and last_message.text:
        return last_message.text
    elif isinstance(last_message.content, str):
        return last_message.content
    elif isinstance(last_message.content, list):
        text_parts = [
            part["text"] for part in last_message.content if isinstance(part, dict) and "text" in part
        ]
        return "\n".join(text_parts) if text_parts else str(last_message.content)

    return str(last_message.content)


def ask(agent: Any, question: str, thread_id: str = "default-session") -> str:
    """Full secure turn: input safety guardrail -> agent -> output safety guardrail.

    Args:
        agent: Compiled LangGraph agent.
        question: User query string.
        thread_id: Session identifier.

    Returns:
        Final response text or safety block message.
    """
    # 1. Screen user input before any LLM or retrieval action
    input_ok, input_reason = check_input(question)
    logger.info("INPUT GUARDRAIL: %s (%s)", "PASS" if input_ok else "BLOCK", input_reason)
    if not input_ok:
        logger.warning("Input blocked by guardrail: %s", input_reason)
        return INPUT_BLOCKED_MESSAGE

    # 2. Invoke the agent
    answer = ask_plain(agent, question, thread_id=thread_id)

    # 3. Screen agent output before returning to user
    output_ok, output_reason = check_output(answer)
    logger.info("OUTPUT GUARDRAIL: %s (%s)", "PASS" if output_ok else "BLOCK", output_reason)
    if not output_ok:
        logger.warning("Output blocked by guardrail: %s", output_reason)
        return OUTPUT_BLOCKED_MESSAGE

    return answer


# Backward compatibility alias
ask_reliably = ask
