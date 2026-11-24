"""backend/app/infrastructure/cache/semantic_cache_adapter.py — Semantic Cache Adapter."""

import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.core.config import settings
from backend.app.domain.ports.cache import CachePort
from backend.app.infrastructure.embeddings.fastembed_adapter import EmbeddingAdapter

logger = logging.getLogger(__name__)


class SemanticCacheAdapter(CachePort):
    """Adapter delivering bounded semantic query caching with cosine similarity."""

    def __init__(
        self,
        threshold: float = settings.SEMANTIC_CACHE_THRESHOLD,
        max_entries: int = settings.SEMANTIC_CACHE_MAX_ENTRIES,
        ttl_seconds: int = settings.SEMANTIC_CACHE_TTL_SECONDS,
    ):
        self.threshold = threshold
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._embedding_adapter = EmbeddingAdapter()
        self._entries: deque = deque(maxlen=max_entries)
        self._last_embedded: Optional[Tuple[str, np.ndarray]] = None

    def _embed(self, question: str) -> np.ndarray:
        if self._last_embedded is not None and self._last_embedded[0] == question:
            return self._last_embedded[1]
        vec = np.asarray(self._embedding_adapter.embed_query(question), dtype=float)
        self._last_embedded = (question, vec)
        return vec

    def _fresh_entries(self) -> List[Dict]:
        now = time.time()
        return [e for e in self._entries if now - e["timestamp"] <= self.ttl_seconds]

    def lookup(self, query: str) -> Tuple[Optional[Any], float, Optional[str]]:
        fresh = self._fresh_entries()
        if not fresh:
            return None, 0.0, None

        q_vec = self._embed(query)
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-9:
            return None, 0.0, None

        best_score = -1.0
        best_entry = None

        for entry in fresh:
            e_vec = entry["embedding"]
            e_norm = np.linalg.norm(e_vec)
            if e_norm < 1e-9:
                continue
            sim = float(np.dot(q_vec, e_vec) / (q_norm * e_norm))
            if sim > best_score:
                best_score = sim
                best_entry = entry

        if best_entry and best_score >= self.threshold:
            logger.info(
                "SEMANTIC CACHE HIT (score=%.3f >= threshold=%.3f, matched: '%s')",
                best_score,
                self.threshold,
                best_entry["question"],
            )
            return best_entry["response"], best_score, best_entry["question"]

        return None, (best_score if best_entry else 0.0), None

    def store(self, query: str, response: Any) -> None:
        try:
            vec = self._embed(query)
            self._entries.append(
                {
                    "embedding": vec,
                    "question": query,
                    "response": response,
                    "timestamp": time.time(),
                }
            )
        except Exception as exc:
            logger.warning("Failed to store entry in semantic cache: %s", exc)

    def clear(self) -> None:
        self._entries.clear()
        self._last_embedded = None
        logger.info("Semantic cache cleared.")

    def __len__(self) -> int:
        return len(self._fresh_entries())
