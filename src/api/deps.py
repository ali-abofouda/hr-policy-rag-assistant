"""src/api/deps.py — FastAPI Dependency Injection providers."""

from functools import lru_cache
from typing import Any, Tuple

from src.security.semantic_cache import SemanticCache
from src.services.chat_service import build_hr_assistant


@lru_cache(maxsize=1)
def get_assistant() -> Tuple[Any, SemanticCache]:
    """Provide singleton compiled LangGraph agent and initialized semantic cache."""
    return build_hr_assistant()
