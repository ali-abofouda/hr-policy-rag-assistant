"""backend/app/domain/ports/vector_store.py — Vector Store Port Interface."""

from typing import Any, List, Optional, Protocol, Tuple, runtime_checkable
from langchain_core.documents import Document


@runtime_checkable
class VectorStorePort(Protocol):
    """Abstract interface defining hybrid search and document persistence."""

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[Any] = None
    ) -> List[Tuple[Document, float]]:
        """Search vector store and return top-k matching documents with scores."""
        ...

    def add_documents(self, documents: List[Document], **kwargs: Any) -> List[str]:
        """Upsert documents into vector collection."""
        ...
