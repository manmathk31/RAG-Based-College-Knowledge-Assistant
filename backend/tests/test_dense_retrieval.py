"""Unit tests for Qdrant dense vector search DenseRetriever."""

from unittest.mock import AsyncMock
import pytest

from app.core.exceptions import DenseRetrievalError
from app.retrieval.dense import DenseRetriever


@pytest.fixture
def mock_embedding_service():
    service = AsyncMock()
    service.embed_single.return_value = [0.05] * 384
    return service


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.search.return_value = [
        {
            "id": "point-1",
            "score": 0.88,
            "payload": {
                "chunk_id": "chunk-101",
                "document_id": "doc-55",
                "document_name": "Library_Rules.pdf",
                "document_version": 2,
                "page_number": 3,
                "section": "Borrowing Limits",
                "content": "Undergraduate students may borrow up to 5 books simultaneously.",
                "is_active": True,
            },
        }
    ]
    return store


@pytest.mark.asyncio
async def test_dense_retrieve_empty_query_returns_empty(mock_embedding_service, mock_vector_store):
    """Verify that an empty or whitespace query returns an empty list immediately."""
    retriever = DenseRetriever(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )

    assert await retriever.retrieve("") == []
    assert await retriever.retrieve("   ") == []
    mock_embedding_service.embed_single.assert_not_called()
    mock_vector_store.search.assert_not_called()


@pytest.mark.asyncio
async def test_dense_retrieve_success(mock_embedding_service, mock_vector_store):
    """Verify dense retrieval embeds the query, searches with is_active filter, and returns candidates."""
    retriever = DenseRetriever(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )

    candidates = await retriever.retrieve("library borrowing limit", limit=5)

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.chunk_id == "chunk-101"
    assert cand.document_id == "doc-55"
    assert cand.document_version == 2
    assert cand.score == 0.88
    assert cand.rank == 1
    assert cand.retrieval_source == "dense"
    assert "up to 5 books" in cand.content

    mock_embedding_service.embed_single.assert_called_once_with("library borrowing limit")
    mock_vector_store.search.assert_called_once()
    _, kwargs = mock_vector_store.search.call_args
    assert kwargs.get("filters") == {"is_active": True}


@pytest.mark.asyncio
async def test_dense_retrieve_vector_store_error_raises_dense_error(mock_embedding_service, mock_vector_store):
    """Verify that vector store failures are wrapped into DenseRetrievalError."""
    mock_vector_store.search.side_effect = Exception("Qdrant cluster unreachable")

    retriever = DenseRetriever(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )

    with pytest.raises(DenseRetrievalError) as exc_info:
        await retriever.retrieve("test question")

    assert "Dense vector retrieval failed" in str(exc_info.value)

