"""src/api/v1/endpoints/chat.py — REST endpoint for HR policy chat completions."""

import re
import time
import uuid
from typing import Any, List, Tuple

from fastapi import APIRouter, Depends, status

from src.api.deps import get_assistant
from src.schemas.chat import ChatRequest, ChatResponse, Citation
from src.security.semantic_cache import SemanticCache
from src.services.chat_service import ask

router = APIRouter(tags=["Chat"])

CITATION_REGEX = re.compile(r"\(Source:\s*([^)]+)\)", re.IGNORECASE)


def _extract_citations(answer: str) -> List[Citation]:
    """Extract cited policy sources from the assistant's answer text."""
    matches = CITATION_REGEX.findall(answer)
    citations: List[Citation] = []
    seen = set()
    for match in matches:
        sources = [s.strip() for s in match.split(",")]
        for src in sources:
            if src and src not in seen:
                seen.add(src)
                citations.append(Citation(source=src))
    return citations


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask an HR policy question",
)
async def chat_endpoint(
    request: ChatRequest,
    assistant_bundle: Tuple[Any, SemanticCache] = Depends(get_assistant),
) -> ChatResponse:
    """Execute grounded retrieval augmented generation against HR policies.

    Includes input/output safety guardrails, semantic caching, and multi-turn thread memory.
    """
    agent, cache = assistant_bundle
    thread_id = request.thread_id or f"session-{uuid.uuid4().hex[:8]}"

    # Check if this query is already in cache
    is_cached = cache.lookup(request.query) is not None

    t0 = time.perf_counter()
    answer = ask(agent, cache, request.query, thread_id=thread_id)
    latency = round(time.perf_counter() - t0, 3)

    citations = _extract_citations(answer)

    return ChatResponse(
        answer=answer,
        thread_id=thread_id,
        is_cached=is_cached,
        latency_seconds=latency,
        citations=citations,
    )
