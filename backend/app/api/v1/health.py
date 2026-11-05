"""Health and readiness check endpoints."""

from fastapi import APIRouter, Depends, Request
from app.core.config import Settings, get_settings
from app.db.session import check_db_connectivity
from app.schemas.health import HealthResponse, ReadinessResponse
from app.vector_store.base import BaseVectorStore

router = APIRouter()


@router.get("", response_model=HealthResponse, summary="API Process Health Check")
async def check_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return the operational health status of the API process."""
    return HealthResponse(
        status="ok",
        project_name=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="0.1.0",
    )


@router.get("/ready", response_model=ReadinessResponse, summary="External Dependency Readiness")
async def check_readiness(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ReadinessResponse:
    """Check connectivity to external vector storage and metadata database without leaking credentials."""
    vector_store: BaseVectorStore = getattr(request.app.state, "vector_store", None)

    qdrant_configured = bool(settings.QDRANT_URL and settings.QDRANT_URL.strip())
    qdrant_connected = False
    details = {}

    if vector_store and hasattr(vector_store, "ping") and qdrant_configured:
        try:
            qdrant_connected = await vector_store.ping()
        except Exception as exc:
            details["qdrant_error"] = str(exc)

    database_configured = bool(settings.DATABASE_URL and settings.DATABASE_URL.strip())
    database_connected = False

    if database_configured:
        try:
            database_connected = await check_db_connectivity()
        except Exception as exc:
            details["database_error"] = str(exc)

    gemini_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    # Degraded if any configured dependency cannot be reached
    is_degraded = (qdrant_configured and not qdrant_connected) or (database_configured and not database_connected)
    overall_status = "degraded" if is_degraded else "ready"

    return ReadinessResponse(
        status=overall_status,
        qdrant_configured=qdrant_configured,
        qdrant_connected=qdrant_connected,
        database_configured=database_configured,
        database_connected=database_connected,
        gemini_configured=gemini_configured,
        gemini_model=settings.GEMINI_GENERATION_MODEL,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dimension=settings.EMBEDDING_DIMENSION,
        details=details if details else None,
    )
