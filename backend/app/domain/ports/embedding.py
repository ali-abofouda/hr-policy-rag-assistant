"""backend/app/domain/ports/embedding.py — Embedding Port Interface."""

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingPort(Protocol):
    """Abstract interface defining text embedding capabilities."""

    @property
    def dimension(self) -> int:
        """Embedding vector dimension."""
        ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute dense embeddings for multiple document strings."""
        ...

    def embed_query(self, text: str) -> List[float]:
        """Compute dense embedding for a single search query."""
        ...
