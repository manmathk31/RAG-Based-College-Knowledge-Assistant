"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.core.config import Settings, get_settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide isolated test settings."""
    return Settings(
        PROJECT_NAME="RAG-Based-College-Knowledge-Assistant-Test",
        ENVIRONMENT="testing",
        DEBUG=True,
        BACKEND_CORS_ORIGINS=["http://localhost:3000"],
        ADMIN_API_SECRET="test-secret",
    )


@pytest.fixture(scope="session")
def client(test_settings: Settings) -> TestClient:
    """Create a FastAPI TestClient with overridden settings."""
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client

