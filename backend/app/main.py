"""Main application entry point for RAG-Based-College-Knowledge-Assistant."""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DatabaseUnavailableError,
    DocumentIngestionFailedError,
    DocumentNotFoundError,
    EmptyDocumentError,
    FileValidationError,
    InvalidDocumentStateError,
    UnsupportedFileFormatError,
)
from app.core.logging import setup_logging
from app.db.session import close_db, init_db
from app.embeddings.base import BaseEmbeddingService
from app.embeddings.huggingface import HuggingFaceEmbeddingService
from app.generation.base import BaseGenerationService
from app.generation.gemini import GeminiGenerationService
from app.ingestion.orchestrator import DocumentIngestionOrchestrator
from app.ingestion.service import DocumentIngestionService
from app.retrieval.engine import HybridRetrievalEngine
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

    # Initialize Metadata Database engine (Supabase PostgreSQL)
    init_db(settings=settings)

    # Initialize Embedding Service and store on app.state
    embedding_service = HuggingFaceEmbeddingService(settings=settings)
    app.state.embedding_service = embedding_service

    # Initialize Qdrant Vector Store and store on app.state
    vector_store = QdrantVectorStore(settings=settings)
    app.state.vector_store = vector_store

    # Initialize Document Ingestion Service and store on app.state
    ingestion_service = DocumentIngestionService(settings=settings)
    app.state.ingestion_service = ingestion_service

    # Initialize Document Ingestion Orchestrator and store on app.state
    orchestrator = DocumentIngestionOrchestrator(
        settings=settings,
        ingestion_service=ingestion_service,
    )
    app.state.orchestrator = orchestrator

    # Initialize Hybrid Retrieval Engine and store on app.state
    retrieval_engine = HybridRetrievalEngine(
        embedding_service=embedding_service,
        vector_store=vector_store,
        settings=settings,
    )
    app.state.retrieval_engine = retrieval_engine

    # Initialize Gemini Generation Service and store on app.state
    generation_service = GeminiGenerationService(settings=settings)
    app.state.generation_service = generation_service

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
    await close_db()
    await embedding_service.close()
    await vector_store.close()


def get_vector_store(request: Request) -> BaseVectorStore:
    """Dependency provider for vector store adapter."""
    return request.app.state.vector_store


def get_embedding_service(request: Request) -> BaseEmbeddingService:
    """Dependency provider for text embedding service."""
    return request.app.state.embedding_service


def get_ingestion_service(request: Request) -> DocumentIngestionService:
    """Dependency provider for document ingestion service."""
    return request.app.state.ingestion_service


def get_orchestrator(request: Request) -> DocumentIngestionOrchestrator:
    """Dependency provider for document ingestion orchestrator."""
    return request.app.state.orchestrator


def get_retrieval_engine(request: Request) -> HybridRetrievalEngine:
    """Dependency provider for hybrid retrieval engine."""
    return getattr(request.app.state, "retrieval_engine", None)


def get_generation_service(request: Request) -> BaseGenerationService:
    """Dependency provider for answer generation service."""
    return getattr(request.app.state, "generation_service", None)


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

    # Domain Exception Handlers
    @app.exception_handler(DatabaseUnavailableError)
    async def database_unavailable_handler(request: Request, exc: DatabaseUnavailableError) -> JSONResponse:
        logger.error("Database unavailable error processing %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DocumentNotFoundError)
    async def document_not_found_handler(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(FileValidationError)
    async def file_validation_handler(request: Request, exc: FileValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnsupportedFileFormatError)
    async def unsupported_format_handler(request: Request, exc: UnsupportedFileFormatError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(InvalidDocumentStateError)
    async def invalid_state_handler(request: Request, exc: InvalidDocumentStateError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(EmptyDocumentError)
    async def empty_document_handler(request: Request, exc: EmptyDocumentError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DocumentIngestionFailedError)
    async def ingestion_failed_handler(request: Request, exc: DocumentIngestionFailedError) -> JSONResponse:
        logger.error("Document ingestion failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
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
