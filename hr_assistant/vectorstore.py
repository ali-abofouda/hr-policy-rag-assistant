"""vectorstore alias module for vector_store to ensure flexible imports."""

from hr_assistant.vector_store import (
    _ID_NAMESPACE,
    _SPARSE_MODEL,
    _qdrant_client,
    _stable_chunk_id,
    build_vector_store,
    collection_exists,
    get_retriever,
    load_vector_store,
)

__all__ = [
    "_ID_NAMESPACE",
    "_SPARSE_MODEL",
    "_qdrant_client",
    "_stable_chunk_id",
    "build_vector_store",
    "collection_exists",
    "get_retriever",
    "load_vector_store",
]
