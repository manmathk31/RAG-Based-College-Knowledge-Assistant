"""User Chat API endpoints for querying college documents with grounded generation."""

import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DatabaseUnavailableError,
    GenerationAuthenticationError,
    GenerationError,
    GenerationRateLimitError,
    GenerationServiceUnavailableError,
    GenerationTimeoutError,
    RetrievalError,
)
from app.db.session import get_db
from app.generation.base import BaseGenerationService
from app.retrieval.engine import HybridRetrievalEngine
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_optional_db(request: Request) -> AsyncGenerator[Optional[AsyncSession], None]:
    """Dependency providing an async database session if available, yielding None if unavailable.

    Ensures chat queries continue functioning via dense-only search if Supabase is down.
    """
    try:
        async for session in get_db():
            yield session
            return
    except DatabaseUnavailableError:
        logger.info("Supabase PostgreSQL unavailable during chat query; falling back to dense Qdrant retrieval.")
        yield None
    except Exception as exc:
        logger.warning("Database connection failed during chat query (%s); falling back to dense retrieval.", exc)
        yield None


def get_retrieval_engine(request: Request) -> HybridRetrievalEngine:
    """FastAPI dependency for the hybrid retrieval engine."""
    return getattr(request.app.state, "retrieval_engine", None)


def get_generation_service(request: Request) -> BaseGenerationService:
    """FastAPI dependency for the LLM answer generation service."""
    return getattr(request.app.state, "generation_service", None)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the college knowledge assistant",
)
@router.post(
    "/query",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Query alias for frontend compatibility",
)
async def chat_query(
    payload: ChatRequest,
    db: Optional[AsyncSession] = Depends(get_optional_db),
    retrieval_engine: HybridRetrievalEngine = Depends(get_retrieval_engine),
    generation_service: BaseGenerationService = Depends(get_generation_service),
) -> ChatResponse:
    """Answer student questions by performing hybrid retrieval over college documents

    and generating grounded answers with exact source citations via Google Gemini.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string must not be empty.",
        )

    query_text = payload.message.strip()

    # 1. Hybrid Retrieval and Context Construction
    try:
        context_text, citations, retrieval_mode, _ = await retrieval_engine.retrieve_and_build_context(
            query=query_text,
            db=db,
        )
    except RetrievalError as r_exc:
        logger.error("Context retrieval failed: %s", r_exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Knowledge retrieval service is currently unavailable: {r_exc}",
        )
    except Exception as exc:
        logger.error("Unexpected error in retrieval engine: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving relevant college documents.",
        )

    # 2. Honest Fallback if No Context Found
    if not citations or not context_text.strip():
        return ChatResponse(
            answer="I could not find information regarding your question in the official college documents.",
            sources=[],
            retrieval_mode=retrieval_mode,
        )

    # 3. Grounded Generation via Gemini
    try:
        history_dicts = [h.model_dump() for h in payload.history] if payload.history else None
        answer = await generation_service.generate_answer(
            query=query_text,
            context_text=context_text,
            history=history_dicts,
        )

        return ChatResponse(
            answer=answer,
            sources=citations,
            retrieval_mode=retrieval_mode,
        )

    except GenerationAuthenticationError as exc:
        logger.error("Gemini authentication failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer generation provider is not properly configured.",
        )
    except (GenerationRateLimitError, GenerationServiceUnavailableError) as exc:
        logger.warning("Gemini capacity error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The answer generation service is currently experiencing high load. Please try again in a few moments.",
        )
    except GenerationTimeoutError as exc:
        logger.warning("Gemini timeout: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Answer generation timed out. Please try asking again.",
        )
    except GenerationError as exc:
        logger.error("Gemini generation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate grounded answer from context.",
        )

