"""Unit tests for PostgreSQL full-text search KeywordRetriever."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.exceptions import KeywordRetrievalError
from app.retrieval.keyword import KeywordRetriever


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.get_points_by_ids.return_value = [
        {
            "id": "chunk-1",
            "payload": {
                "chunk_id": "chunk-1",
                "content": "Students must maintain at least 75% attendance to appear in semester exams.",
                "document_name": "Academic_Regulations.pdf",
                "page_number": 4,
                "section": "Attendance Policy",
            },
        },
        {
            "id": "chunk-2",
            "payload": {
                "chunk_id": "chunk-2",
                "content": "Tuition fees must be paid before the start of each academic semester.",
                "document_name": "Fee_Schedule.pdf",
                "page_number": 2,
                "section": "Payment Terms",
            },
        },
    ]
    return store


@pytest.mark.asyncio
async def test_keyword_retrieve_empty_or_punctuation_query_returns_empty(mock_vector_store):
    """Verify that empty, whitespace, or punctuation-only queries exit immediately."""
    retriever = KeywordRetriever(vector_store=mock_vector_store)
    mock_db = AsyncMock()

    assert await retriever.retrieve("", db=mock_db) == []
    assert await retriever.retrieve("   ", db=mock_db) == []
    assert await retriever.retrieve("??? !!! ...", db=mock_db) == []
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_keyword_retrieve_success(mock_vector_store):
    """Verify that matching rows in PostgreSQL return mapped RetrievalCandidates with text from Qdrant."""
    retriever = KeywordRetriever(vector_store=mock_vector_store)

    row1 = MagicMock(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_version=1,
        page_number=4,
        section_title="Attendance Policy",
        original_filename="Academic_Regulations.pdf",
        rank_score=0.75,
    )
    row2 = MagicMock(
        chunk_id="chunk-2",
        document_id="doc-2",
        document_version=1,
        page_number=2,
        section_title="Payment Terms",
        original_filename="Fee_Schedule.pdf",
        rank_score=0.45,
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [row1, row2]
    mock_db.execute.return_value = mock_res

    candidates = await retriever.retrieve("attendance requirement", db=mock_db, limit=5)

    assert len(candidates) == 2
    assert candidates[0].chunk_id == "chunk-1"
    assert candidates[0].score == 0.75
    assert candidates[0].rank == 1
    assert candidates[0].retrieval_source == "keyword"
    assert "75% attendance" in candidates[0].content

    assert candidates[1].chunk_id == "chunk-2"
    assert candidates[1].score == 0.45
    assert candidates[1].rank == 2


@pytest.mark.asyncio
async def test_keyword_retrieve_database_failure_raises_keyword_error(mock_vector_store):
    """Verify that database errors are wrapped cleanly into KeywordRetrievalError."""
    retriever = KeywordRetriever(vector_store=mock_vector_store)
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("PostgreSQL query execution error")

    with pytest.raises(KeywordRetrievalError) as exc_info:
        await retriever.retrieve("valid query", db=mock_db)

    assert "PostgreSQL keyword search failed" in str(exc_info.value)

