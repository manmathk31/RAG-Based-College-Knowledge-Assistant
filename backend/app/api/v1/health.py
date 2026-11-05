"""Health check endpoint to verify backend process availability."""

from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse, summary="API Health Check")
async def check_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return the operational health status of the API service."""
    return HealthResponse(
        status="ok",
        project_name=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="0.1.0",
    )

