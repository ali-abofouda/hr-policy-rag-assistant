"""14 · semantic_cache — In-memory semantic caching for query acceleration and cost optimization.

Embeds each question with the local/configured embeddings model, keeping a bounded in-memory
deque of (embedding, question, answer, timestamp). On incoming queries, computes cosine
similarity against all active entries.

If best similarity >= config.SEMANTIC_CACHE_THRESHOLD (default 0.93):
  Returns cached response immediately in ~0.01s, skipping retrieval, re-ranking, and LLM generation.

Bounded retention:
  - config.SEMANTIC_CACHE_MAX_ENTRIES: Evicts oldest entries on capacity (FIFO).
  - config.SEMANTIC_CACHE_TTL_SECONDS: Ignores stale answers past expiration window.
"""

import logging
import time
from collections import deque
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    from langsmith import traceable
except ImportError:
    def traceable(name=None, **kwargs):
        def decorator(fn):
            return fn
        return decorator

from hr_assistant import config
from hr_assistant.embeddings import get_embeddings_model

logger = logging.getLogger(__name__)


class SemanticCache:
    """Bounded in-memory semantic cache using cosine similarity over embeddings."""

    def __init__(
        self,
        threshold: float = config.SEMANTIC_CACHE_THRESHOLD,
        max_entries: int = config.SEMANTIC_CACHE_MAX_ENTRIES,
        ttl_seconds: int = config.SEMANTIC_CACHE_TTL_SECONDS,
    ):
        self.threshold = threshold
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._embeddings_model = get_embeddings_model()
        self._entries: deque = deque(maxlen=max_entries)
        self._last_embedded: Optional[Tuple[str, np.ndarray]] = None

    def _embed(self, question: str) -> np.ndarray:
        """Compute or reuse normalized embedding vector for query."""
        if self._last_embedded is not None and self._last_embedded[0] == question:
            return self._last_embedded[1]
        vec = np.asarray(self._embeddings_model.embed_query(question), dtype=float)
        self._last_embedded = (question, vec)
        return vec

    def _fresh_entries(self) -> List[Dict]:
        """Return cached entries that have not exceeded TTL expiration."""
        if self.ttl_seconds <= 0:
            return list(self._entries)
        cutoff = time.monotonic() - self.ttl_seconds
        return [e for e in self._entries if e["stored_at"] >= cutoff]

    @traceable(name="semantic_cache_lookup")
    def lookup(self, question: str) -> Optional[str]:
        """Return cached answer for semantically similar question, or None on cache miss.

        Args:
            question: User inquiry string.

        Returns:
            Cached response string if similarity >= threshold, else None.
        """
        entries = self._fresh_entries()
        if not entries:
            logger.debug("Semantic cache miss (cache empty)")
            return None

        raw = self._embed(question)
        norm_raw = np.linalg.norm(raw) or 1.0
        query_vec = raw / norm_raw

        # Vectorized cosine similarity computation across all cached entries
        matrix = np.vstack([e["embedding"] for e in entries])
        row_norms = np.linalg.norm(matrix, axis=1)
        row_norms[row_norms == 0] = 1.0
        normalized_matrix = matrix / row_norms[:, None]
        scores = normalized_matrix @ query_vec

        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])

        if best_score >= self.threshold:
            best = entries[best_idx]
            logger.info(
                "SEMANTIC CACHE HIT (score=%.3f >= threshold=%.3f, matched: '%s') — skipping RAG + LLM",
                best_score,
                self.threshold,
                best["question"],
            )
            return best["answer"]

        logger.debug("Semantic cache miss (best score=%.3f < threshold=%.3f)", best_score, self.threshold)
        return None

    def store(self, question: str, answer: str) -> None:
        """Store (question, answer) pair into cache with current timestamp.

        Args:
            question: Cleaned user query string.
            answer: Verified generated answer string.
        """
        # Reuses lookup()'s embedding when question matches
        self._entries.append(
            {
                "embedding": self._embed(question),
                "question": question,
                "answer": answer,
                "stored_at": time.monotonic(),
            }
        )
        logger.debug("Stored query into semantic cache. Total cached: %d", len(self._entries))

    def clear(self) -> None:
        """Evict all entries from cache."""
        self._entries.clear()
        self._last_embedded = None
        logger.debug("Semantic cache cleared.")
