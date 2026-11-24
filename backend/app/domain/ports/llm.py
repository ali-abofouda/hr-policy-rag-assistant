"""backend/app/domain/ports/llm.py — LLM Port Interface."""

from typing import Any, List, Optional, Protocol, runtime_checkable
from langchain_core.messages import BaseMessage


@runtime_checkable
class LLMPort(Protocol):
    """Abstract interface defining LLM interaction capabilities."""

    def invoke(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        """Synchronously generate completion for messages."""
        ...

    async def ainvoke(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        """Asynchronously generate completion for messages."""
        ...
