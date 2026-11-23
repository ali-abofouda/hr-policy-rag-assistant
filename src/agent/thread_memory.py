"""15 · thread_memory — Conversational state and checkpointer operations for the agent.

Coordinates operations on the agent's checkpointer across conversational turns:
- invoke_agent: Execute one turn, safely extracting text across various message shapes.
- record_turn: Persist (HumanMessage, AIMessage) into thread state without LLM execution (on cache hits).
- overwrite_answer: Swap a blocked unsafe message with safety sentinel in memory to avoid context poisoning.
- input_text_for_screening: Aggregate current question with recent human turns for multi-turn attack screening.
"""

import logging
from typing import Any, Dict, List
from langchain_core.messages import AIMessage, HumanMessage

from src.core import config

logger = logging.getLogger(__name__)


def thread_config(thread_id: str) -> Dict[str, Any]:
    """Generate configuration dictionary for LangGraph checkpointer."""
    return {"configurable": {"thread_id": thread_id}}


def invoke_agent(agent: Any, question: str, thread_id: str) -> Any:
    """Run one turn through the agent and return the final message object.

    Extracts `.text` or `.content` gracefully to handle thought signatures
    from modern models (e.g. Gemini 2.5 / 3.5).
    """
    response = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config=thread_config(thread_id),
    )
    return response["messages"][-1]


def record_turn(agent: Any, thread_id: str, question: str, answer: str) -> None:
    """Append a (question, answer) turn to checkpointer state without running the agent.

    Essential for semantic cache hits so subsequent follow-ups ('tell me more about that')
    retain full conversational context.
    """
    try:
        agent.update_state(
            thread_config(thread_id),
            {"messages": [HumanMessage(content=question), AIMessage(content=answer)]},
        )
        logger.debug("Recorded cache-hit turn into thread memory '%s'", thread_id)
    except Exception as exc:
        logger.debug("Could not record cache-hit turn to thread memory: %s", exc)


def overwrite_answer(agent: Any, thread_id: str, ai_message: Any, replacement: str) -> None:
    """Replace an unsafe response in thread memory with replacement text.

    Uses message ID matching so blocked answers do not linger in conversation context
    for subsequent turns.
    """
    msg_id = getattr(ai_message, "id", None)
    if not msg_id:
        return
    try:
        agent.update_state(
            thread_config(thread_id),
            {"messages": [AIMessage(id=msg_id, content=replacement)]},
        )
        logger.debug("Overwrote blocked response '%s' in thread memory", msg_id)
    except Exception as exc:
        logger.debug("Could not overwrite blocked response in thread memory: %s", exc)


def input_text_for_screening(agent: Any, question: str, thread_id: str) -> str:
    """Aggregate recent user turns with current question for multi-turn guardrail screening.

    Screens multi-turn attacks that appear benign turn-by-turn but adversarial in aggregate.
    Only human messages are included — never assistant answers or tool outputs.
    """
    turns = config.GUARDRAIL_HISTORY_TURNS
    if turns <= 0:
        return question

    try:
        state = agent.get_state(thread_config(thread_id))
        messages = (getattr(state, "values", None) or {}).get("messages", [])
    except Exception as exc:
        logger.debug("Could not read conversation history for screening: %s", exc)
        return question

    prior: List[str] = []
    # Collect only prior human messages up to configured history turns
    human_messages = [msg for msg in messages if getattr(msg, "type", "") == "human"]
    for msg in human_messages[-turns:]:
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        clean_content = str(content).strip()
        if clean_content:
            prior.append(clean_content)

    if not prior:
        return question

    # Return plain newline concatenation of user history + current question
    return "\n".join([*prior, question])
