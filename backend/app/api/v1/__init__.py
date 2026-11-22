"""API v1 router assembly."""

from fastapi import APIRouter
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.nlp import router as nlp_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, prefix="/health", tags=["Health"])
api_v1_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_v1_router.include_router(nlp_router, prefix="/nlp", tags=["NLP Lab (CO2)"])

__all__ = ["api_v1_router"]

