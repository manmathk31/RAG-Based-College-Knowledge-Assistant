"""API v1 router assembly."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, prefix="/health", tags=["Health"])

__all__ = ["api_v1_router"]

