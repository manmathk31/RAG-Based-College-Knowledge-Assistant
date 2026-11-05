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
from app.schemas.health import HealthResponse

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown events."""
    settings = get_settings()
    setup_logging(debug=settings.DEBUG)
    logger.info("Starting %s in %s mode", settings.PROJECT_NAME, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


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
        logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=settings.DEBUG)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred. Please contact the administrator."},
        )

    # Mount API v1 Routers
    app.include_router(api_v1_router)

    # Root convenience health endpoint
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
