"""src/api/v1/router.py — Consolidate v1 endpoints."""

from fastapi import APIRouter
from src.api.v1.endpoints.chat import router as chat_router
from src.api.v1.endpoints.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="")
api_router.include_router(chat_router, prefix="")
