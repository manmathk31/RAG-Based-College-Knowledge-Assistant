"""Main application entry point for RAG-Based-College-Knowledge-Assistant."""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.embeddings.base import BaseEmbeddingService
from app.embeddings.huggingface import HuggingFaceEmbeddingService
from app.schemas.health import HealthResponse
from app.vector_store.base import BaseVectorStore
from app.vector_store.qdrant import QdrantVectorStore

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup, dependency lifecycles, and graceful shutdown."""
    settings = get_settings()
    setup_logging(debug=settings.DEBUG)
    logger.info("Starting %s in %s mode", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # Initialize Embedding Service and store on app.state
    embedding_service = HuggingFaceEmbeddingService(settings=settings)
    app.state.embedding_service = embedding_service

    # Initialize Qdrant Vector Store and store on app.state
    vector_store = QdrantVectorStore(settings=settings)
    app.state.vector_store = vector_store

    # Optional eager initialization of Qdrant collection if configured
    if settings.QDRANT_URL.strip():
        try:
            await vector_store.create_collection_if_not_exists(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vector_size=settings.EMBEDDING_DIMENSION,
            )
            logger.info("Qdrant collection '%s' is ready.", settings.QDRANT_COLLECTION_NAME)
        except Exception as exc:
            logger.warning(
                "Could not connect to Qdrant or initialize collection at startup: %s. "
                "Application will start in degraded mode.",
                exc,
            )

    yield

    logger.info("Shutting down %s", settings.PROJECT_NAME)
    await embedding_service.close()
    await vector_store.close()


def get_vector_store(request: Request) -> BaseVectorStore:
    """Dependency provider for vector store adapter."""
    return request.app.state.vector_store


def get_embedding_service(request: Request) -> BaseEmbeddingService:
    """Dependency provider for text embedding service."""
    return request.app.state.embedding_service


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Modular Monolith Backend for College Knowledge Assistant (RAG)",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS Configuration
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception processing %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
            exc_info=settings.DEBUG,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred. Please contact the administrator."},
        )

    # Mount API v1 Routers
    app.include_router(api_v1_router)

    # Root convenience health endpoint (Process availability)
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def root_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
        return HealthResponse(
            status="ok",
            project_name=settings.PROJECT_NAME,
            environment=settings.ENVIRONMENT,
            version="0.1.0",
        )

    return app


app = create_application()
