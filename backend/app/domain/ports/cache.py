"""backend/app/domain/ports/cache.py — Semantic Cache Port Interface."""

from typing import Any, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class CachePort(Protocol):
    """Abstract interface for semantic query-response caching."""

    def lookup(self, query: str) -> Tuple[Optional[Any], float, Optional[str]]:
        """Look up query; return (cached_response, similarity_score, matched_query)."""
        ...

    def store(self, query: str, response: Any) -> None:
        """Store query and response pair in the semantic cache."""
        ...

    def clear(self) -> None:
        """Evict all entries from the cache."""
        ...
