"""backend/app/infrastructure/rerankers/cross_encoder_adapter.py — Reranker Adapter."""

import logging
from typing import List, Tuple
import numpy as np
import requests
from langchain_core.documents import Document

from backend.app.core.config import settings
from backend.app.domain.ports.reranker import RerankerPort
from backend.app.infrastructure.embeddings.fastembed_adapter import EmbeddingAdapter

logger = logging.getLogger(__name__)
JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"
_DOC_EMBEDDINGS_CACHE: dict = {}


class RerankerAdapter(RerankerPort):
    """Adapter executing Jina Cloud CrossEncoder or local semantic re-scoring."""

    def __init__(self):
        self.embedding_adapter = EmbeddingAdapter()

    def _local_rerank(self, query: str, candidates: List[Document], top_n: int) -> List[Document]:
        needed, needed_idx, vecs = [], [], [None] * len(candidates)
        for i, c in enumerate(candidates):
            text = c.page_content
            if text in _DOC_EMBEDDINGS_CACHE:
                vecs[i] = _DOC_EMBEDDINGS_CACHE[text]
            else:
                needed.append(text)
                needed_idx.append(i)

        if needed:
            new_vecs = self.embedding_adapter.embed_documents(needed)
            for idx, text, v in zip(needed_idx, needed, new_vecs):
                arr = np.array(v, dtype=float)
                _DOC_EMBEDDINGS_CACHE[text] = arr
                vecs[idx] = arr

        doc_vecs = np.array(vecs, dtype=float)
        query_vec = np.array(self.embedding_adapter.embed_query(query))
        norm_q = np.linalg.norm(query_vec)
        norm_docs = np.linalg.norm(doc_vecs, axis=1)
        scores = np.dot(doc_vecs, query_vec) / (norm_docs * norm_q + 1e-9)

        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:top_n]]

    def rerank(self, query: str, documents: List[Document], top_n: int = 5) -> List[Document]:
        if not documents:
            return []
        if settings.JINA_API_KEY and settings.JINA_API_KEY.strip():
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.JINA_API_KEY}",
                }
                payload = {
                    "model": settings.RERANKER_MODEL_NAME,
                    "query": query,
                    "top_n": top_n,
                    "documents": [d.page_content for d in documents],
                }
                resp = requests.post(JINA_RERANK_URL, headers=headers, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    return [documents[r["index"]] for r in results if r["index"] < len(documents)]
            except Exception as exc:
                logger.warning("Jina rerank failed (%s). Falling back to local re-scoring.", exc)

        return self._local_rerank(query, documents, top_n)
