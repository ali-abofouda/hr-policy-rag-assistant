"""backend/app/api/router.py — Consolidated API Router."""

from fastapi import APIRouter
from backend.app.api.routes import chat, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router, prefix="/api/v1")

__all__ = ["api_router"]
