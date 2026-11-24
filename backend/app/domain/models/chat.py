"""backend/app/domain/models/chat.py — Domain Entities for Chat and Guardrail interactions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Citation:
    """Citable source piece returned by the RAG pipeline."""
    source: str
    content_snippet: Optional[str] = None
    score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailResult:
    """Outcome of safety guardrail evaluation."""
    passed: bool
    reason: str
    blocked: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Domain response produced by the HR Policy Assistant."""
    answer: str
    thread_id: str
    is_cached: bool = False
    latency_seconds: float = 0.0
    citations: List[Citation] = field(default_factory=list)
    guardrail_status: Optional[str] = None
