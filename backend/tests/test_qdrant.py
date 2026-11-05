"""Targeted unit tests for Qdrant Cloud vector-store adapter."""

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from qdrant_client import models

from app.core.config import Settings
from app.core.exceptions import (
    CollectionConfigurationMismatchError,
    VectorStoreConnectionError,
    VectorStoreOperationError,
)
from app.vector_store.qdrant import QdrantVectorStore


@pytest.fixture
def test_store_settings() -> Settings:
    return Settings(
        QDRANT_URL="https://mock-cluster.qdrant.io:6333",
        QDRANT_API_KEY="mock-api-key",
        QDRANT_COLLECTION_NAME="college_knowledge_base",
        QDRANT_TIMEOUT=5.0,
        EMBEDDING_DIMENSION=384,
    )


@pytest.mark.asyncio
async def test_create_collection_when_not_exists(test_store_settings: Settings) -> None:
    """Verify that when a collection does not exist, it is created with Cosine distance and a payload index."""
    mock_client = MagicMock()
    mock_client.collection_exists = AsyncMock(return_value=False)
    mock_client.create_collection = AsyncMock()
    mock_client.create_payload_index = AsyncMock()

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    await store.create_collection_if_not_exists("test_col", vector_size=384)

    mock_client.collection_exists.assert_called_once_with("test_col")
    mock_client.create_collection.assert_called_once()
    call_kwargs = mock_client.create_collection.call_args[1]
    assert call_kwargs["collection_name"] == "test_col"
    assert call_kwargs["vectors_config"].size == 384
    assert call_kwargs["vectors_config"].distance == models.Distance.COSINE

    # Verify payload index creation for document_id
    mock_client.create_payload_index.assert_called_once_with(
        collection_name="test_col",
        field_name="document_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


@pytest.mark.asyncio
async def test_validate_existing_collection_compatible(test_store_settings: Settings) -> None:
    """Verify that an existing collection with matching size and Cosine distance passes validation."""
    mock_client = MagicMock()
    mock_client.collection_exists = AsyncMock(return_value=True)

    # Mock collection info response with 384-dim Cosine vector
    mock_info = MagicMock()
    mock_info.config.params.vectors = models.VectorParams(size=384, distance=models.Distance.COSINE)
    mock_client.get_collection = AsyncMock(return_value=mock_info)

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    await store.create_collection_if_not_exists("test_col", vector_size=384)

    mock_client.collection_exists.assert_called_once_with("test_col")
    mock_client.get_collection.assert_called_once_with("test_col")
    # create_collection should NOT be called since it exists
    assert not hasattr(mock_client.create_collection, "assert_called") or mock_client.create_collection.call_count == 0


@pytest.mark.asyncio
async def test_validate_existing_collection_mismatch_raises(test_store_settings: Settings) -> None:
    """Verify that a mismatch in vector dimension (e.g. 768 vs 384) raises CollectionConfigurationMismatchError."""
    mock_client = MagicMock()
    mock_client.collection_exists = AsyncMock(return_value=True)

    # Collection has 768 dimensions (from legacy model), but expected is 384
    mock_info = MagicMock()
    mock_info.config.params.vectors = models.VectorParams(size=768, distance=models.Distance.COSINE)
    mock_client.get_collection = AsyncMock(return_value=mock_info)

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    with pytest.raises(CollectionConfigurationMismatchError, match="size=768"):
        await store.create_collection_if_not_exists("test_col", vector_size=384)


@pytest.mark.asyncio
async def test_upsert_points_and_id_normalization(test_store_settings: Settings) -> None:
    """Verify upsert maps dict points to PointStructs and handles deterministic ID normalization."""
    mock_client = MagicMock()
    mock_client.upsert = AsyncMock()

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)

    raw_points = [
        {
            "id": "chunk_doc1_p1_c0",  # String ID should convert to UUID5
            "vector": [0.1] * 384,
            "payload": {
                "document_id": "doc1",
                "document_name": "Handbook.pdf",
                "page_number": 1,
                "chunk_id": "chunk_doc1_p1_c0",
                "content": "College library hours: 8am to 8pm.",
            },
        },
        {
            "id": 12345,  # Integer ID should remain integer
            "vector": [0.2] * 384,
            "payload": {"document_id": "doc2", "page_number": 2},
        },
    ]

    success = await store.upsert_points("test_col", raw_points)
    assert success is True
    mock_client.upsert.assert_called_once()

    call_kwargs = mock_client.upsert.call_args[1]
    point_structs = call_kwargs["points"]
    assert len(point_structs) == 2

    # Verify ID 1 is a valid UUID string derived from chunk_doc1_p1_c0
    expected_uuid5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "chunk_doc1_p1_c0"))
    assert point_structs[0].id == expected_uuid5
    assert point_structs[0].payload["document_id"] == "doc1"

    # Verify ID 2 remains integer
    assert point_structs[1].id == 12345


@pytest.mark.asyncio
async def test_search_results_mapping(test_store_settings: Settings) -> None:
    """Verify vector search executes and maps ScoredPoint results to predictable dicts."""
    mock_client = MagicMock()

    mock_scored = [
        models.ScoredPoint(
            id=str(uuid.uuid4()),
            version=1,
            score=0.912,
            payload={"document_id": "doc1", "content": "Sample content snippet", "page_number": 3},
            vector=None,
        )
    ]
    mock_client.search = AsyncMock(return_value=mock_scored)

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    results = await store.search("test_col", query_vector=[0.1] * 384, limit=5)

    assert len(results) == 1
    assert results[0]["score"] == pytest.approx(0.912, rel=1e-3)
    assert results[0]["payload"]["document_id"] == "doc1"
    assert results[0]["payload"]["page_number"] == 3


@pytest.mark.asyncio
async def test_search_with_metadata_filters(test_store_settings: Settings) -> None:
    """Verify search properly builds Qdrant models.Filter from dictionary filters."""
    mock_client = MagicMock()
    mock_client.search = AsyncMock(return_value=[])

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    await store.search(
        "test_col",
        query_vector=[0.1] * 384,
        limit=3,
        filters={"document_id": "doc_xyz", "section": "Admissions"},
    )

    mock_client.search.assert_called_once()
    call_kwargs = mock_client.search.call_args[1]
    query_filter: models.Filter = call_kwargs["query_filter"]
    assert isinstance(query_filter, models.Filter)
    assert len(query_filter.must) == 2


@pytest.mark.asyncio
async def test_delete_by_document_id(test_store_settings: Settings) -> None:
    """Verify points associated with a document_id are deleted via FilterSelector."""
    mock_client = MagicMock()
    mock_client.delete = AsyncMock()

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    success = await store.delete_by_document_id("test_col", "doc_to_delete")

    assert success is True
    mock_client.delete.assert_called_once()
    call_kwargs = mock_client.delete.call_args[1]
    points_selector = call_kwargs["points_selector"]
    assert isinstance(points_selector, models.FilterSelector)

    # Empty document_id should raise ValueError
    with pytest.raises(ValueError, match="must be a non-empty string"):
        await store.delete_by_document_id("test_col", "")


@pytest.mark.asyncio
async def test_operation_failure_wrapping(test_store_settings: Settings) -> None:
    """Verify unexpected Qdrant client errors are wrapped in VectorStoreOperationError."""
    mock_client = MagicMock()
    mock_client.search = AsyncMock(side_effect=RuntimeError("Qdrant internal failure"))

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    with pytest.raises(VectorStoreOperationError, match="Vector search failed"):
        await store.search("test_col", [0.1] * 384)


@pytest.mark.asyncio
async def test_store_close(test_store_settings: Settings) -> None:
    """Verify close() terminates the underlying AsyncQdrantClient."""
    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    store = QdrantVectorStore(settings=test_store_settings, client=mock_client)
    store._owns_client = True
    await store.close()

    mock_client.close.assert_called_once()

