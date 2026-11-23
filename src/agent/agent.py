"""13 · agent — LangGraph/LangChain agent uniting LLM, search tool, prompt, and memory.

Coordinates:
- Brain: LLM (Google Gemini / LiteLLM Router).
- Tool: HR policy search and re-ranking tool ('search_hr_policy').
- System Prompt: Rigorous HR behavioral guidelines, citations, and out-of-domain fences.
- Memory: Short-term conversation persistence via Checkpointer (MemorySaver).

Two variants:
  create_hr_agent          — Unguarded SYSTEM_PROMPT (used for red-team baseline).
  create_reliability_agent — Hardened RELIABILITY_SYSTEM_PROMPT with identity lock (used in production).
"""

import logging
from typing import Any, List, Optional, Sequence
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from src.agent import prompts

logger = logging.getLogger(__name__)


def _build_agent(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
    checkpointer: Optional[Any] = None,
) -> Any:
    """Shared builder for compiling agents with specified system prompt and memory."""
    logger.info("Assembling agent with %d tool(s) and checkpointer=%s...", len(tools), checkpointer is not None)

    kwargs = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        **kwargs,
    )


def create_hr_agent(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    checkpointer: Optional[Any] = None,
) -> Any:
    """Create and return plain HR Assistant agent for baseline comparisons."""
    return _build_agent(llm, tools, prompts.SYSTEM_PROMPT, checkpointer=checkpointer)


def create_reliability_agent(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    checkpointer: Optional[Any] = None,
) -> Any:
    """Create and return hardened Reliability HR Assistant agent for production."""
    return _build_agent(llm, tools, prompts.RELIABILITY_SYSTEM_PROMPT, checkpointer=checkpointer)
