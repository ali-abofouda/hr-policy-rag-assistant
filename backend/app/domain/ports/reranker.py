"""backend/app/domain/ports/reranker.py — Reranker Port Interface."""

from typing import List, Protocol, runtime_checkable
from langchain_core.documents import Document


@runtime_checkable
class RerankerPort(Protocol):
    """Abstract interface defining second-stage CrossEncoder reranking."""

    def rerank(self, query: str, documents: List[Document], top_n: int = 5) -> List[Document]:
        """Score and reorder candidate documents against the query."""
        ...
