"""13 · agent — LangGraph/LangChain agent uniting LLM, search tool, prompt, and memory.

Coordinates:
- Brain: LLM (Google Gemini via Vertex AI or Google AI Studio).
- Tool: HR policy search and re-ranking tool ('search_hr_policy').
- System Prompt: Rigorous HR behavioral guidelines, citations, and out-of-domain fences.
- Memory: Short-term conversation persistence via Checkpointer (MemorySaver).
"""

import logging
from typing import Any, List, Optional, Sequence
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from hr_assistant import prompts

logger = logging.getLogger(__name__)


def create_hr_agent(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    checkpointer: Optional[Any] = None,
) -> Any:
    """Create and return the compiled HR Assistant agent.

    The checkpointer (e.g. MemorySaver) provides multi-turn conversational memory,
    allowing follow-up questions to retain context without repeating prior inquiries.

    Args:
        llm: Initialized chat model instance acting as the agent brain.
        tools: Sequence of callable tools (e.g., [search_hr_policy]).
        checkpointer: Optional persistence checkpointer for conversation memory.

    Returns:
        CompiledStateGraph agent instance ready for invocation.
    """
    logger.info("Assembling HR Agent with %d tool(s) and checkpointer=%s...", len(tools), checkpointer is not None)

    kwargs = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=prompts.SYSTEM_PROMPT,
        **kwargs,
    )
