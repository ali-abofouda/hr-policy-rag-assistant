"""backend/app/api/routes/chat.py — Chat API endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.schemas.chat import ChatRequest, ChatResponse, Citation
from backend.app.core.logging import logger
from backend.app.dependencies import get_chat_service
from backend.app.domain.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, summary="Query HR Policies")
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Execute grounded RAG query over company HR policies."""
    thread_id = request.thread_id or str(uuid.uuid4())
    logger.info("Executing chat query [thread_id=%s]: '%s'", thread_id, request.query[:80])

    try:
        domain_response = chat_service.ask(question=request.query, thread_id=thread_id)

        citations = [
            Citation(
                source=c.source,
                content_snippet=c.content_snippet,
                score=c.score,
            )
            for c in domain_response.citations
        ]

        return ChatResponse(
            answer=domain_response.answer,
            thread_id=domain_response.thread_id,
            is_cached=domain_response.is_cached,
            latency_seconds=domain_response.latency_seconds,
            citations=citations,
        )
    except Exception as exc:
        logger.error("Error executing chat query: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the request: {str(exc)}",
        )
