"""10 · reranker — Re-rank retrieved candidate chunks for precision retrieval.

Hybrid retrieval (vector + BM25) is fast and recall-oriented, returning a wider
candidate shortlist (config.RERANK_CANDIDATE_K = 12). The re-ranker reads the user
question and each candidate chunk together, scoring relevance to select the
top N cited chunks (config.TOP_K_RESULTS = 5).

Supported Engines:
1. Jina AI Cross-Encoder API via config.JINA_API_KEY and config.RERANKER_MODEL_NAME.
2. Local Semantic Re-scoring Fallback (FastEmbed Jina Embeddings cosine scoring)
   ensuring 100% offline zero-cost execution when Jina API tokens are unavailable.
"""

import logging
from typing import List, Optional, Tuple
import numpy as np
import requests

from langchain_core.documents import Document

from hr_assistant import config
from hr_assistant.embeddings import get_embeddings_model

logger = logging.getLogger(__name__)

JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"

# In-memory document embedding cache to prevent redundant ONNX embeddings on CPU
_DOC_EMBEDDINGS_CACHE: dict = {}


def _get_candidate_vectors(candidates: List[Document], embeddings_model) -> np.ndarray:
    """Retrieve document vectors from in-memory cache, batch-embedding only unseen chunks."""
    needed = []
    needed_idx = []
    vecs = [None] * len(candidates)

    for i, c in enumerate(candidates):
        text = c.page_content
        if text in _DOC_EMBEDDINGS_CACHE:
            vecs[i] = _DOC_EMBEDDINGS_CACHE[text]
        else:
            needed.append(text)
            needed_idx.append(i)

    if needed:
        logger.debug("Embedding %d new candidate chunk(s) for local re-ranking cache...", len(needed))
        new_vecs = embeddings_model.embed_documents(needed)
        for idx, text, v in zip(needed_idx, needed, new_vecs):
            arr = np.array(v, dtype=float)
            _DOC_EMBEDDINGS_CACHE[text] = arr
            vecs[idx] = arr

    return np.array(vecs, dtype=float)


def _local_semantic_rerank_with_scores(
    query: str,
    candidates: List[Document],
    top_n: int,
) -> List[Tuple[Document, float]]:
    """Score and re-rank candidates locally using cosine similarity with cached embeddings.

    Args:
        query: User input query string.
        candidates: Retrieved candidate Document objects.
        top_n: Number of top documents to return.

    Returns:
        Sorted list of (Document, relevance_score) tuples.
    """
    try:
        embeddings_model = get_embeddings_model()
        query_vec = np.array(embeddings_model.embed_query(query))
        doc_vecs = _get_candidate_vectors(candidates, embeddings_model)

        # Compute cosine similarities: dot(q, d) / (||q|| * ||d||)
        norm_q = np.linalg.norm(query_vec)
        norm_docs = np.linalg.norm(doc_vecs, axis=1)
        scores = np.dot(doc_vecs, query_vec) / (norm_docs * norm_q + 1e-9)

        ranked_indices = np.argsort(scores)[::-1]
        top_indices = ranked_indices[:top_n]
        return [(candidates[i], float(scores[i])) for i in top_indices]
    except Exception as exc:
        logger.warning("Local semantic re-scoring fallback encountered notice: %s. Truncating candidates.", exc)
        return [(c, 0.5) for c in candidates[:top_n]]


def rerank_with_scores(
    query: str,
    candidates: List[Document],
    top_n: int = config.TOP_K_RESULTS,
) -> List[Tuple[Document, float]]:
    """Re-rank candidates returning (Document, relevance_score) pairs.

    The guarded search tool uses these scores to gate on relevance floor,
    preventing weakly related or off-topic context from being passed to the model.

    Args:
        query: User question or search query.
        candidates: Candidate Document objects from retrieval.
        top_n: Maximum number of ranked results.

    Returns:
        List of (Document, score) tuples, highest score first.
    """
    if not candidates or top_n <= 0:
        return []

    # Attempt Jina AI Cross-Encoder API if an API key is set
    if config.JINA_API_KEY and config.JINA_API_KEY.strip():
        try:
            logger.info("Executing Jina Cross-Encoder re-ranking for %d candidates...", len(candidates))
            response = requests.post(
                JINA_RERANK_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config.JINA_API_KEY}",
                },
                json={
                    "model": config.RERANKER_MODEL_NAME,
                    "query": query,
                    "top_n": top_n,
                    "documents": [c.page_content for c in candidates],
                    "return_documents": False,
                },
                timeout=30,
            )
            response.raise_for_status()

            # Map result indices back to candidate Document objects
            ranked = response.json().get("results", [])
            return [(candidates[r["index"]], float(r["relevance_score"])) for r in ranked]
        except Exception as exc:
            logger.warning(
                "Jina Cross-Encoder API unavailable (%s). Falling back to local semantic re-scoring.",
                exc,
            )

    # Local fallback re-ranking
    logger.info("Executing local semantic re-scoring for %d candidates...", len(candidates))
    return _local_semantic_rerank_with_scores(query=query, candidates=candidates, top_n=top_n)


def rerank(
    query: str,
    candidates: List[Document],
    top_n: int = config.TOP_K_RESULTS,
) -> List[Document]:
    """Re-rank candidate documents against user query, returning Document list only.

    Args:
        query: User question or search query.
        candidates: Candidate Document objects from retrieval.
        top_n: Number of highest-relevance documents to return.

    Returns:
        Re-ranked list of Document objects, trimmed to top_n.
    """
    return [doc for doc, _score in rerank_with_scores(query, candidates, top_n=top_n)]
