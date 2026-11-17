"""08 · vector_store — Store chunk embeddings in Qdrant Cloud and execute hybrid search.

Features:
- Hybrid Search: Combines dense vector similarity (Jina Embeddings) with sparse keyword matching (BM25 via FastEmbed).
- Deterministic Upsert: Generates stable UUIDs from chunk source and text, preventing duplicate records upon re-ingestion.
- Metadata Filtering: Builds a keyword payload index on metadata.policy_category for scoped queries.
- Singleton Client: Uses @lru_cache to pool QdrantClient HTTP/gRPC connections across the process lifecycle.
"""

import logging
import uuid
from functools import lru_cache
from typing import List, Optional, Set, Union

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, PayloadSchemaType

from hr_assistant import config
from hr_assistant.embeddings import get_embeddings_model

logger = logging.getLogger(__name__)

# Fixed namespace UUID for deterministic chunk point generation
_ID_NAMESPACE: uuid.UUID = uuid.UUID("5b9c1a1e-8b1a-4f7d-9d5e-2b6a7c9d1e3f")

# BM25 sparse model for keyword search
_SPARSE_MODEL: str = "Qdrant/bm25"


@lru_cache(maxsize=1) # Cache the QdrantClient instance for connection reuse across the process
def _qdrant_client() -> QdrantClient:
    """Initialize and cache a singleton QdrantClient instance for connection reuse.

    Returns:
        Configured QdrantClient connected to Qdrant Cloud or local cluster.
    """
    return QdrantClient(
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY or None,
    )


def collection_exists(collection_name: str) -> bool:
    """Check whether a collection exists in Qdrant and contains at least one indexed point.

    Args:
        collection_name: Name of the collection to inspect.

    Returns:
        True if the collection exists and contains indexed points, False otherwise.
    """
    client = _qdrant_client()
    try:
        if not client.collection_exists(collection_name):
            return False
        return client.count(collection_name).count > 0
    except Exception as exc:
        logger.warning("Error checking collection '%s': %s", collection_name, exc)
        return False


def _stable_chunk_id(chunk: Document) -> str: # Deterministic UUID5 generation for chunk point IDs
    """Generate a deterministic UUID5 point ID from chunk source and content text.

    Ensures idempotent upsert behavior: re-running ingestion updates existing
    points in place rather than inserting duplicate records.

    Args:
        chunk: LangChain Document chunk.

    Returns:
        Deterministic string UUID.
    """
    source = chunk.metadata.get("source", "")
    key = f"{source}::{chunk.page_content}"
    return str(uuid.uuid5(_ID_NAMESPACE, key))


def load_vector_store(
    collection_name: str = config.QDRANT_COLLECTION_NAME,
    hybrid: bool = True,
) -> QdrantVectorStore:
    """Connect to an existing Qdrant collection for query execution (no upsert).

    Args:
        collection_name: Target Qdrant collection name.
        hybrid: Whether to enable dense + sparse hybrid retrieval mode.

    Returns:
        Configured QdrantVectorStore attached to the target collection.

    Raises:
        RuntimeError: If the target collection is missing or empty.
    """
    if not collection_exists(collection_name):
        raise RuntimeError(
            f"Qdrant collection '{collection_name}' is missing or empty. "
            f"Run the ingestion pipeline to populate the corpus before querying."
        )

    kwargs = {
        "collection_name": collection_name,
        "embedding": get_embeddings_model(),
        "url": config.QDRANT_URL,
        "api_key": config.QDRANT_API_KEY or None,
    }

    if hybrid:
        kwargs["sparse_embedding"] = FastEmbedSparse(model_name=_SPARSE_MODEL)
        kwargs["retrieval_mode"] = RetrievalMode.HYBRID
    else:
        kwargs["retrieval_mode"] = RetrievalMode.DENSE

    logger.info("Connecting to existing Qdrant collection: %s (hybrid=%s)", collection_name, hybrid)
    return QdrantVectorStore.from_existing_collection(**kwargs)


def build_vector_store(
    chunks: List[Document],
    hybrid: bool = True,
    collection_name: str = config.QDRANT_COLLECTION_NAME,
) -> QdrantVectorStore:
    """Embed document chunks and upsert them into Qdrant Cloud.

    Configures hybrid dense + sparse indexing and establishes a payload index
    on metadata.policy_category for scoped retrieval.

    Args:
        chunks: List of split Document chunks to embed and upsert.
        hybrid: Whether to compute sparse BM25 vectors alongside dense embeddings.
        collection_name: Target collection name in Qdrant.

    Returns:
        Populated QdrantVectorStore instance.
    """
    embeddings_model = get_embeddings_model()
    point_ids = [_stable_chunk_id(chunk) for chunk in chunks]

    kwargs = {
        "documents": chunks,
        "embedding": embeddings_model,
        "ids": point_ids,
        "url": config.QDRANT_URL,
        "api_key": config.QDRANT_API_KEY or None,
        "collection_name": collection_name,
    }

    if hybrid:
        kwargs["sparse_embedding"] = FastEmbedSparse(model_name=_SPARSE_MODEL)
        kwargs["retrieval_mode"] = RetrievalMode.HYBRID
    else:
        kwargs["retrieval_mode"] = RetrievalMode.DENSE

    logger.info("Upserting %d chunks into Qdrant collection '%s' (hybrid=%s)...", len(chunks), collection_name, hybrid)
    store = QdrantVectorStore.from_documents(**kwargs)

    # Establish keyword payload index on metadata.policy_category for filtered queries
    try:
        store.client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.policy_category",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Created payload index on 'metadata.policy_category' in '%s'.", collection_name)
    except Exception as exc:
        logger.debug("Payload index creation notice (may already exist): %s", exc)

    return store


def get_retriever(
    vector_store: QdrantVectorStore,
    k: int = config.TOP_K_RESULTS,
    filter_categories: Optional[Union[Set[str], List[str]]] = None,
) -> VectorStoreRetriever:
    """Construct a retriever instance with optional category-based metadata filtering.

    Args:
        vector_store: Active QdrantVectorStore instance.
        k: Maximum number of candidate chunks to retrieve.
        filter_categories: Optional allow-list of policy categories to filter results.

    Returns:
        Configured VectorStoreRetriever ready for chain integration.
    """
    search_kwargs = {"k": k}

    if filter_categories:
        categories_list = list(filter_categories)
        search_kwargs["filter"] = Filter(
            must=[
                FieldCondition(
                    key="metadata.policy_category",
                    match=MatchAny(any=categories_list),
                )
            ]
        )

    return vector_store.as_retriever(search_kwargs=search_kwargs)
