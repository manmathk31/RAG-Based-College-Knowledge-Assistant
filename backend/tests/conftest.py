"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.core.config import Settings, get_settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide isolated test settings without external network dependencies."""
    return Settings(
        PROJECT_NAME="RAG-Based-College-Knowledge-Assistant-Test",
        ENVIRONMENT="testing",
        DEBUG=True,
        BACKEND_CORS_ORIGINS=["http://localhost:3000"],
        ADMIN_API_SECRET="test-secret",
        HF_TOKEN="",
        EMBEDDING_PROVIDER="huggingface",
        EMBEDDING_MODEL="BAAI/bge-small-en-v1.5",
        EMBEDDING_DIMENSION=384,
        EMBEDDING_BATCH_SIZE=2,
        EMBEDDING_TIMEOUT=5.0,
        EMBEDDING_MAX_RETRIES=2,
        QDRANT_URL="",
        QDRANT_API_KEY="",
        QDRANT_COLLECTION_NAME="test_collection",
        QDRANT_TIMEOUT=5.0,
    )


@pytest.fixture(scope="session")
def client(test_settings: Settings) -> TestClient:
    """Create a FastAPI TestClient with overridden settings and lifespan execution."""
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
