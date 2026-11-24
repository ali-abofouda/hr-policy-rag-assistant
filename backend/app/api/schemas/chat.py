"""backend/app/api/schemas/chat.py — Pydantic v2 schemas for chat endpoints."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The employee's inquiry regarding company HR policy.",
        examples=["How many days of paid annual leave do I get?"],
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional session/thread identifier for multi-turn conversational memory.",
        examples=["user-session-1234"],
    )


class Citation(BaseModel):
    source: str = Field(..., description="Filename or category of the cited policy document.")
    content_snippet: Optional[str] = Field(default=None, description="Relevant excerpt from the policy chunk.")
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Relevance score.")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded response text citing source policy documents.")
    thread_id: str = Field(..., description="Active thread session identifier.")
    is_cached: bool = Field(default=False, description="Whether resolved via Semantic Cache.")
    latency_seconds: float = Field(default=0.0, ge=0.0, description="Latency in seconds.")
    citations: List[Citation] = Field(default_factory=list, description="Policy documents referenced.")
