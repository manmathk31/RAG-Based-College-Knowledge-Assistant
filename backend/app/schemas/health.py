"""Health and readiness check response models."""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for basic API process health status."""

    status: str = Field(default="ok", description="Operational status of backend process")
    project_name: str = Field(description="Name of the application")
    environment: str = Field(description="Deployment environment")
    version: str = Field(description="Application version")


class ReadinessResponse(BaseModel):
    """Schema for dependency readiness and connectivity status."""

    status: str = Field(description="'ready' or 'degraded'")
    qdrant_configured: bool = Field(description="Whether QDRANT_URL is configured")
    qdrant_connected: bool = Field(description="Live connectivity to Qdrant cluster")
    database_configured: bool = Field(default=False, description="Whether DATABASE_URL is configured")
    database_connected: bool = Field(default=False, description="Live connectivity to Supabase PostgreSQL")
    gemini_configured: bool = Field(default=False, description="Whether GEMINI_API_KEY is configured")
    gemini_model: str = Field(description="Configured Gemini generative model identifier")
    embedding_provider: str = Field(description="Configured embedding provider name")
    embedding_model: str = Field(description="Configured embedding model identifier")
    embedding_dimension: int = Field(description="Configured embedding vector dimension")
    details: Optional[Dict[str, str]] = Field(default=None, description="Safe diagnostic details")
