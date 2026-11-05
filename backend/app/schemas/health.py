"""Health check response models."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for API health status check."""

    status: str = Field(default="ok", description="Operational status of backend")
    project_name: str = Field(description="Name of the application")
    environment: str = Field(description="Deployment environment")
    version: str = Field(description="Application version")

