"""11 · tools — Wrap vector retrieval and re-ranking as LangChain agent tools.

Retriever-as-a-Tool Pattern:
1. Wide hybrid retrieval: Query Qdrant for top candidates (config.RERANK_CANDIDATE_K = 12).
2. Deep re-ranking: Score and filter candidates down to the most relevant (config.TOP_K_RESULTS = 5).
3. Grounded context formatting: Join chunks with document sources [Source: <filename>] for citations.
"""

import logging
from typing import Callable
from langchain_core.tools import BaseTool, tool
from langchain_qdrant import QdrantVectorStore

from hr_assistant import config
from hr_assistant.reranker import rerank
from hr_assistant.vector_store import get_retriever

logger = logging.getLogger(__name__)


def create_search_tool(vector_store: QdrantVectorStore) -> BaseTool:
    """Create a LangChain @tool function that searches and re-ranks the HR policy corpus.

    Args:
        vector_store: Configured QdrantVectorStore instance attached to HR corpus.

    Returns:
        Callable BaseTool instance named 'search_hr_policy'.
    """

    @tool
    def search_hr_policy(question: str) -> str:
        """Search the HR policy documents for information about leave,
        work from home, probation, notice period, reimbursement, code of conduct,
        holidays, maternity/paternity leave, travel expenses, or the exit process."""
        logger.info("Tool invoked: search_hr_policy with query: '%s'", question)

        retriever = get_retriever(vector_store, k=config.RERANK_CANDIDATE_K)
        candidates = retriever.invoke(question)
        logger.info("Retrieved %d candidate chunks from vector store.", len(candidates))

        top_chunks = rerank(question, candidates, top_n=config.TOP_K_RESULTS)
        logger.info("Re-ranked down to %d top chunks.", len(top_chunks))

        if not top_chunks:
            return "No matching HR policy clauses found in company documentation."

        return "\n\n".join(
            f"[Source: {c.metadata.get('source', 'Unknown Document')}]\n{c.page_content}"
            for c in top_chunks
        )

    return search_hr_policy
