"""src/api/deps.py — FastAPI Dependency Injection providers."""

from functools import lru_cache
from typing import Tuple, Any
from src.services.pipeline import build_hr_assistant
from src.services.semantic_cache import SemanticCache


@lru_cache(maxsize=1)
def get_assistant() -> Tuple[Any, SemanticCache]:
    """Provide singleton compiled LangGraph agent and initialized semantic cache."""
    return build_hr_assistant()
