"""11 · tools — Wrap vector retrieval and re-ranking as LangChain agent tools.

Retriever-as-a-Tool Pattern:
1. Wide hybrid retrieval: Query Qdrant for top candidates (config.RERANK_CANDIDATE_K = 12).
2. Deep re-ranking: Score and filter candidates down to the most relevant (config.TOP_K_RESULTS = 5).
3. Grounded context formatting: Join chunks with document sources [Source: <filename>] for citations.

create_guarded_search_tool(): Production tool with two-layer scope guardrails:
  1. Category allow-list (config.HR_POLICY_CATEGORIES) hard filter at retrieval level.
  2. Post-rerank relevance score floor (config.RELEVANCE_THRESHOLD). If below floor,
     returns NOT_FOUND_SENTINEL to prompt polite declination.

create_search_tool(): Unguarded baseline tool kept for red-team comparisons.
"""

import logging
from typing import Callable
from langchain_core.tools import BaseTool, tool
from langchain_qdrant import QdrantVectorStore

from src.core import config
from src.retrieval.reranker import rerank, rerank_with_scores
from src.retrieval.vector_store import get_retriever

logger = logging.getLogger(__name__)

NOT_FOUND_SENTINEL = "NOT_FOUND: no relevant HR policy content matched this question."


def create_search_tool(vector_store: QdrantVectorStore) -> BaseTool:
    """Create an unguarded LangChain @tool function for baseline red-team testing.

    Args:
        vector_store: Configured QdrantVectorStore instance attached to corpus.

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


def create_guarded_search_tool(vector_store: QdrantVectorStore) -> BaseTool:
    """Guarded version of the search tool implementing a two-layer scope guardrail:

    1. Retrieval is hard-filtered to config.HR_POLICY_CATEGORIES — non-HR
       chunks (Finance/Sales/Operations/Business) are rejected at vector lookup.
    2. The re-ranked top result must clear config.RELEVANCE_THRESHOLD (e.g. 0.35),
       or the tool returns NOT_FOUND_SENTINEL rather than passing low-relevance noise.
    """

    @tool
    def search_hr_policy(question: str) -> str:
        """Search the HR policy documents for information about leave, work from home,
        probation, notice period, reimbursement, code of conduct, holidays, maternity/
        paternity leave, travel expenses, or the exit process.

        Do not use this for Finance, Sales, Operations, or Business questions — it will not find anything."""
        logger.info("Guarded search tool invoked for query: '%s'", question)

        retriever = get_retriever(
            vector_store,
            k=config.RERANK_CANDIDATE_K,
            filter_categories=config.HR_POLICY_CATEGORIES,
        )
        candidates = retriever.invoke(question)
        if not candidates:
            logger.info("No candidates matched category filter '%s'.", config.HR_POLICY_CATEGORIES)
            return NOT_FOUND_SENTINEL

        ranked = rerank_with_scores(question, candidates, top_n=config.TOP_K_RESULTS)
        if not ranked or ranked[0][1] < config.RELEVANCE_THRESHOLD:
            top_score = ranked[0][1] if ranked else 0.0
            logger.info(
                "Top re-ranked candidate score %.3f below relevance threshold %.3f. Returning NOT_FOUND.",
                top_score,
                config.RELEVANCE_THRESHOLD,
            )
            return NOT_FOUND_SENTINEL

        logger.info(
            "Guarded search returning %d chunks. Top score: %.3f.",
            len(ranked),
            ranked[0][1],
        )
        return "\n\n".join(
            f"[Source: {c.metadata.get('source', 'Unknown Document')}] (relevance: {score:.2f})\n{c.page_content}"
            for c, score in ranked
        )

    return search_hr_policy
