"""src/schemas/health.py — Pydantic v2 schemas for health checks and liveness probes."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """Health check status for an individual subsystem."""

    name: str = Field(..., description="Subsystem name (e.g. qdrant, gemini_gateway, semantic_cache).")
    status: str = Field(..., description="Operational status: 'healthy', 'degraded', or 'unreachable'.")
    details: Optional[str] = Field(default=None, description="Diagnostic details or response latency.")


class HealthResponse(BaseModel):
    """Comprehensive health check response for container liveness and readiness probes."""

    status: str = Field(..., description="Overall service status: 'healthy' or 'degraded'.")
    version: str = Field(default="1.0.0", description="Application service version.")
    components: List[ComponentStatus] = Field(default_factory=list, description="Subsystem diagnostics.")
