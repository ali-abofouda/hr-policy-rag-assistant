"""backend/app/infrastructure/vectorstore/qdrant_adapter.py — Qdrant Vector Store Adapter."""

import logging
import uuid
from typing import Any, List, Optional, Tuple
from langchain_core.documents import Document
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient

from backend.app.core.config import settings
from backend.app.domain.ports.vector_store import VectorStorePort
from backend.app.infrastructure.embeddings.fastembed_adapter import EmbeddingAdapter

logger = logging.getLogger(__name__)
_ID_NAMESPACE: uuid.UUID = uuid.UUID("5b9c1a1e-8b1a-4f7d-9d5e-2b6a7c9d1e3f")
_SPARSE_MODEL: str = "Qdrant/bm25"


class QdrantAdapter(VectorStorePort):
    """Adapter managing Qdrant Cloud connection, hybrid collections, and search queries."""

    def __init__(self, collection_name: Optional[str] = None, hybrid: bool = True):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.hybrid = hybrid
        self._client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        self._embedding_adapter = EmbeddingAdapter()
        self._vector_store: Optional[QdrantVectorStore] = None

    def exists(self) -> bool:
        """Return True if collection exists and has points."""
        try:
            if not self._client.collection_exists(self.collection_name):
                return False
            return self._client.count(self.collection_name).count > 0
        except Exception as exc:
            logger.warning("Error checking collection '%s': %s", self.collection_name, exc)
            return False

    def get_vector_store(self) -> QdrantVectorStore:
        if self._vector_store is None:
            sparse_embeddings = FastEmbedSparse(model_name=_SPARSE_MODEL) if self.hybrid else None
            retrieval_mode = RetrievalMode.HYBRID if self.hybrid else RetrievalMode.DENSE
            self._vector_store = QdrantVectorStore(
                client=self._client,
                collection_name=self.collection_name,
                embedding=self._embedding_adapter.get_embeddings_model(),
                sparse_embedding=sparse_embeddings,
                retrieval_mode=retrieval_mode,
            )
        return self._vector_store

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[Any] = None
    ) -> List[Tuple[Document, float]]:
        store = self.get_vector_store()
        return store.similarity_search_with_score(query, k=k, filter=filter)

    def add_documents(self, documents: List[Document], **kwargs: Any) -> List[str]:
        store = self.get_vector_store()
        ids = [str(uuid.uuid5(_ID_NAMESPACE, f"{d.metadata.get('source', '')}::{d.page_content}")) for d in documents]
        return store.add_documents(documents, ids=ids, **kwargs)
