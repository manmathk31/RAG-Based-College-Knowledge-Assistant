"""Integration tests for User Chat API endpoints (/api/v1/chat and /api/v1/chat/query)."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.chat import get_generation_service, get_optional_db, get_retrieval_engine
from app.core.exceptions import (
    GenerationRateLimitError,
    GenerationTimeoutError,
    RetrievalError,
)
from app.main import app
from app.retrieval.models import SourceCitation


@pytest.fixture
def mock_retrieval_engine():
    engine = AsyncMock()
    citation = SourceCitation(
        citation_id="1",
        document_id="doc-academic",
        document_name="Academic_Policy_2025.pdf",
        document_version=1,
        page_number=4,
        section="Attendance Requirements",
        chunk_id="chunk-1",
        snippet="Students must maintain 75% attendance...",
    )
    context_text = "[1] Document: Academic_Policy_2025.pdf (Page 4, Section: Attendance Requirements)\nStudents must maintain 75% attendance..."
    engine.retrieve_and_build_context.return_value = (context_text, [citation], "hybrid", [])
    return engine


@pytest.fixture
def mock_generation_service():
    service = AsyncMock()
    service.generate_answer.return_value = "According to the academic policy [1], students must maintain at least 75% attendance."
    return service


@pytest.mark.asyncio
async def test_chat_valid_query_success(mock_retrieval_engine, mock_generation_service):
    """Verify successful question returns grounded answer, source citations, and retrieval mode."""
    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval_engine
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    app.dependency_overrides[get_optional_db] = lambda: None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What is the attendance policy for semester exams?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "[1]" in data["answer"]
        assert len(data["sources"]) == 1
        assert data["sources"][0]["citation_id"] == "1"
        assert data["sources"][0]["document_name"] == "Academic_Policy_2025.pdf"
        assert data["retrieval_mode"] == "hybrid"
        assert "request_id" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_query_alias_compatibility(mock_retrieval_engine, mock_generation_service):
    """Verify that POST /api/v1/chat/query with {'question': '...'} works identically."""
    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval_engine
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    app.dependency_overrides[get_optional_db] = lambda: None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/query",
                json={"question": "What is the fee payment deadline?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["sources"]) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_empty_message_returns_422_or_400():
    """Verify that empty question returns validation error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json={"message": "   "})
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_chat_no_relevant_documents_returns_honest_fallback(mock_retrieval_engine, mock_generation_service):
    """Verify that when no chunks match, honest fallback answer is returned with empty sources."""
    mock_retrieval_engine.retrieve_and_build_context.return_value = ("", [], "none", [])

    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval_engine
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    app.dependency_overrides[get_optional_db] = lambda: None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "When is the annual sports festival?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "could not find information" in data["answer"].lower()
        assert data["sources"] == []
        assert data["retrieval_mode"] == "none"
        mock_generation_service.generate_answer.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_supabase_unavailable_falls_back_to_dense_only(mock_retrieval_engine, mock_generation_service):
    """Verify that when Supabase is unavailable, chat query still succeeds with dense_only retrieval."""
    mock_retrieval_engine.retrieve_and_build_context.return_value = (
        "[1] Context excerpt",
        [SourceCitation(citation_id="1", document_id="d1", document_name="Doc.pdf", chunk_id="c1", snippet="snip")],
        "dense_only",
        [],
    )

    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval_engine
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    # Database yields None (unavailable)
    app.dependency_overrides[get_optional_db] = lambda: None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What are grading scales?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["retrieval_mode"] == "dense_only"
        assert len(data["sources"]) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_both_retrieval_fail_returns_503(mock_retrieval_engine, mock_generation_service):
    """Verify that when all retrieval systems fail, 503 Service Unavailable is returned."""
    mock_retrieval_engine.retrieve_and_build_context.side_effect = RetrievalError("All retrieval systems down")

    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval_engine
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    app.dependency_overrides[get_optional_db] = lambda: None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What is syllabus?"},
            )

        assert response.status_code == 503
        assert "retrieval service is currently unavailable" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_gemini_rate_limit_returns_503(mock_retrieval_engine, mock_generation_service):
    """Verify that when Gemini is overloaded, 503 Service Unavailable is returned with friendly message."""
    mock_generation_service.generate_answer.side_effect = GenerationRateLimitError("Quota exceeded")

    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval_engine
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    app.dependency_overrides[get_optional_db] = lambda: None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What is syllabus?"},
            )

        assert response.status_code == 503
        assert "experiencing high load" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_gemini_timeout_returns_504(mock_retrieval_engine, mock_generation_service):
    """Verify that when Gemini times out, 504 Gateway Timeout is returned."""
    mock_generation_service.generate_answer.side_effect = GenerationTimeoutError("Timeout after retries")

    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval_engine
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    app.dependency_overrides[get_optional_db] = lambda: None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What is syllabus?"},
            )

        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

