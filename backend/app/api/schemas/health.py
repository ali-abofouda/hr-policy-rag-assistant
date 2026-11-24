"""backend/app/api/schemas/health.py — Health Check schemas."""

from typing import Dict
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Overall service status (ok | degraded | down).")
    version: str = Field(..., description="Application semantic version.")
    environment: str = Field(..., description="Target execution environment.")
    components: Dict[str, str] = Field(default_factory=dict, description="Health status of external dependencies.")
