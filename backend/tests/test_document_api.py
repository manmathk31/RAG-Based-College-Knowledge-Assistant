"""Integration tests for document management API endpoints (/api/v1/documents)."""

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.documents import (
    get_embedding_service,
    get_orchestrator,
    get_vector_store,
)
from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.models import DocumentModel
from app.db.session import get_db
from app.main import app
from app.schemas.document import DocumentDetailResponse


@pytest.fixture
def admin_headers():
    settings = get_settings()
    return {"X-Admin-Secret": settings.ADMIN_API_SECRET}


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session


@pytest.fixture
def mock_orchestrator():
    orchestrator = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    return store


@pytest.fixture
def mock_embedding_service():
    service = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_upload_missing_admin_secret_returns_401():
    """Verify that requests missing X-Admin-Secret are rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_invalid_admin_secret_returns_401():
    """Verify that requests with invalid X-Admin-Secret are rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            headers={"X-Admin-Secret": "wrong-secret-token"},
            files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_valid_document_returns_201(
    admin_headers,
    mock_db_session,
    mock_orchestrator,
    mock_vector_store,
    mock_embedding_service,
):
    """Verify successful upload and processing returns 201 Created with document payload."""
    now = datetime.now(timezone.utc)
    mock_doc = DocumentModel(
        id="doc-test-123",
        original_filename="Academic_Calendar_2025.pdf",
        normalized_filename="academic_calendar_2025.pdf",
        file_type="pdf",
        file_size=500,
        content_hash="hash123",
        document_version=1,
        status="completed",
        chunk_count=5,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_staged = MagicMock()
    mock_orchestrator.stage_and_validate_upload.return_value = mock_staged
    mock_orchestrator.ingest_document.return_value = (mock_doc, "created", False)

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/documents",
                headers=admin_headers,
                files={"file": ("Academic_Calendar_2025.pdf", b"%PDF-1.4 test", "application/pdf")},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "created"
        assert data["is_duplicate"] is False
        assert data["document"]["id"] == "doc-test-123"
        assert data["document"]["document_version"] == 1
        assert data["document"]["chunk_count"] == 5
        mock_staged.cleanup.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_exact_duplicate_returns_201_with_duplicate_flag(
    admin_headers,
    mock_db_session,
    mock_orchestrator,
    mock_vector_store,
    mock_embedding_service,
):
    """Verify that uploading an exact duplicate reports duplicate_skipped."""
    now = datetime.now(timezone.utc)
    mock_doc = DocumentModel(
        id="doc-test-123",
        original_filename="Academic_Calendar_2025.pdf",
        normalized_filename="academic_calendar_2025.pdf",
        file_type="pdf",
        file_size=500,
        content_hash="hash123",
        document_version=1,
        status="completed",
        chunk_count=5,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_staged = MagicMock()
    mock_orchestrator.stage_and_validate_upload.return_value = mock_staged
    mock_orchestrator.ingest_document.return_value = (mock_doc, "duplicate_skipped", True)

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/documents",
                headers=admin_headers,
                files={"file": ("Academic_Calendar_2025.pdf", b"%PDF-1.4 test", "application/pdf")},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "duplicate_skipped"
        assert data["is_duplicate"] is True
        assert "exact duplicate" in data["message"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_database_unavailable_returns_503(
    admin_headers,
    mock_orchestrator,
    mock_vector_store,
    mock_embedding_service,
):
    """Verify that if database is unreachable, upload endpoint fails with 503."""
    async def failing_db():
        raise DatabaseUnavailableError("Supabase PostgreSQL connection failed.")
        yield

    mock_staged = MagicMock()
    mock_orchestrator.stage_and_validate_upload.return_value = mock_staged

    app.dependency_overrides[get_db] = failing_db
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/documents",
                headers=admin_headers,
                files={"file": ("Handbook.pdf", b"%PDF-1.4 test", "application/pdf")},
            )

        assert response.status_code == 503
        assert "Supabase PostgreSQL connection failed" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_document_by_id_success(
    admin_headers,
    mock_db_session,
):
    """Verify retrieving document metadata by ID."""
    now = datetime.now(timezone.utc)
    mock_doc = DocumentModel(
        id="doc-found-id",
        original_filename="Fee_Structure.docx",
        normalized_filename="fee_structure.docx",
        file_type="docx",
        file_size=1200,
        content_hash="h123",
        document_version=1,
        status="completed",
        chunk_count=3,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_doc
    mock_db_session.execute.return_value = mock_res

    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/documents/doc-found-id", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc-found-id"
        assert data["file_type"] == "docx"
        assert data["status"] == "completed"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_document_by_id_not_found_returns_404(
    admin_headers,
    mock_db_session,
):
    """Verify 404 is returned when document ID does not exist."""
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_res

    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/documents/missing-id", headers=admin_headers)

        assert response.status_code == 404
        assert "missing-id" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_document_success(
    admin_headers,
    mock_db_session,
    mock_orchestrator,
    mock_vector_store,
):
    """Verify DELETE /api/v1/documents/{document_id} deletes vectors and Supabase records."""
    mock_orchestrator.delete_document_and_vectors.return_value = ("del-id", [1, 2], True)

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/documents/del-id", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "del-id"
        assert data["deleted_versions"] == [1, 2]
        assert data["vectors_deleted"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_documents_pagination_and_filtering(
    admin_headers,
    mock_db_session,
):
    """Verify listing documents with pagination and status filters."""
    now = datetime.now(timezone.utc)
    docs = [
        DocumentModel(
            id=f"doc-{i}",
            original_filename=f"Doc_{i}.pdf",
            normalized_filename=f"doc_{i}.pdf",
            file_type="pdf",
            file_size=1000,
            content_hash=f"hash-{i}",
            document_version=1,
            status="completed",
            chunk_count=3,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        for i in range(2)
    ]

    res_count = MagicMock()
    res_count.scalar.return_value = 2

    res_items = MagicMock()
    res_items.scalars.return_value.all.return_value = docs

    mock_db_session.execute.side_effect = [res_count, res_items]
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/documents?skip=0&limit=10&status=completed", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == "doc-0"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_retry_failed_document_api_success(
    admin_headers,
    mock_db_session,
    mock_orchestrator,
    mock_vector_store,
    mock_embedding_service,
):
    """Verify POST /api/v1/documents/{document_id}/retry re-processes a failed document."""
    now = datetime.now(timezone.utc)
    updated_doc = DocumentModel(
        id="retry-doc-id",
        original_filename="Policy.pdf",
        normalized_filename="policy.pdf",
        file_type="pdf",
        file_size=800,
        content_hash="newhash",
        document_version=1,
        status="completed",
        chunk_count=4,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_staged = MagicMock()
    mock_orchestrator.stage_and_validate_upload.return_value = mock_staged
    mock_orchestrator.retry_failed_document.return_value = updated_doc

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/documents/retry-doc-id/retry",
                headers=admin_headers,
                files={"file": ("Policy.pdf", b"%PDF-1.4 sample", "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["document"]["id"] == "retry-doc-id"
        assert data["document"]["status"] == "completed"
        assert "successfully re-ingested" in data["message"]
        mock_staged.cleanup.assert_called_once()
    finally:
        app.dependency_overrides.clear()

