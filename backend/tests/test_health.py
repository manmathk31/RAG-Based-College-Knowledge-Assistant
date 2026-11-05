"""Targeted tests for health-check and readiness endpoints."""

from fastapi.testclient import TestClient


def test_root_health_endpoint(client: TestClient) -> None:
    """Verify that GET /health returns 200 OK and expected schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] == "testing"
    assert data["version"] == "0.1.0"
    assert "project_name" in data


def test_v1_health_endpoint(client: TestClient) -> None:
    """Verify that GET /api/v1/health returns 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] == "testing"


def test_v1_readiness_endpoint(client: TestClient) -> None:
    """Verify that GET /api/v1/health/ready returns 200 OK with safe dependency readiness status."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "qdrant_configured" in data
    assert "qdrant_connected" in data
    assert data["embedding_provider"] == "huggingface"
    assert data["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert data["embedding_dimension"] == 384
    # Ensure no secrets or API keys are exposed
    assert "HF_TOKEN" not in data
    assert "QDRANT_API_KEY" not in data
