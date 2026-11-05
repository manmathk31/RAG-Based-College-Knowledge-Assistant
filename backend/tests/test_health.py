"""Targeted tests for health-check endpoints."""

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

