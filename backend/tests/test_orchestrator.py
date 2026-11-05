"""Unit tests for DocumentIngestionOrchestrator: duplicates, versioning, rollback, and deletion."""

from datetime import datetime, timezone
import io
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.core.exceptions import (
    DocumentIngestionFailedError,
    DocumentNotFoundError,
    InvalidDocumentStateError,
)
from app.db.models import DocumentModel
from app.ingestion.models import DocumentChunk, ExtractedBlock, ExtractedDocument, ExtractedPage
from app.ingestion.orchestrator import (
    DocumentIngestionOrchestrator,
    StagedUpload,
)


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.upsert_points.return_value = True
    store.delete_by_document_id.return_value = True
    return store


@pytest.fixture
def mock_embedding_service():
    service = AsyncMock()
    service.embed_batch.return_value = [[0.1] * 384, [0.2] * 384]
    return service


@pytest.fixture
def mock_ingestion_service():
    service = AsyncMock()
    doc = ExtractedDocument(
        document_id="doc-123",
        filename="Handbook.pdf",
        file_type="pdf",
        pages=[ExtractedPage(page_number=1, text="Test page content", char_count=17)],
        blocks=[ExtractedBlock(text="Test page content", block_type="paragraph", page_number=1)],
        total_pages=1,
        total_chars=17,
    )
    chunks = [
        DocumentChunk(
            chunk_id="chunk-1",
            document_id="doc-123",
            chunk_index=0,
            content="Chunk 1 content",
            token_count=10,
            char_count=15,
            page_number=1,
            source_filename="Handbook.pdf",
            file_type="pdf",
        ),
        DocumentChunk(
            chunk_id="chunk-2",
            document_id="doc-123",
            chunk_index=1,
            content="Chunk 2 content",
            token_count=12,
            char_count=15,
            page_number=1,
            source_filename="Handbook.pdf",
            file_type="pdf",
        ),
    ]
    service.process_document.return_value = (doc, chunks)
    return service


@pytest.fixture
def staged_upload():
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.write(fd, b"%PDF-1.4 sample content")
    os.close(fd)
    staged = StagedUpload(
        temp_path=path,
        original_filename="Handbook.pdf",
        normalized_filename="handbook.pdf",
        file_type="pdf",
        file_size=23,
        content_hash="abc123hash",
    )
    yield staged
    staged.cleanup()


@pytest.mark.asyncio
async def test_ingest_exact_duplicate_skipped(
    staged_upload,
    mock_vector_store,
    mock_embedding_service,
    mock_ingestion_service,
):
    """Verify that an exact duplicate returns existing record without re-indexing."""
    existing_doc = DocumentModel(
        id="existing-doc-id",
        original_filename="Handbook.pdf",
        normalized_filename="handbook.pdf",
        file_type="pdf",
        file_size=23,
        content_hash="abc123hash",
        document_version=1,
        status="completed",
        is_active=True,
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_doc
    mock_db.execute.return_value = mock_result

    orchestrator = DocumentIngestionOrchestrator(ingestion_service=mock_ingestion_service)
    doc, action, is_dup = await orchestrator.ingest_document(
        staged=staged_upload,
        db=mock_db,
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )

    assert doc.id == "existing-doc-id"
    assert action == "duplicate_skipped"
    assert is_dup is True
    # Verify embedding and upsert were never called
    mock_embedding_service.embed_batch.assert_not_called()
    mock_vector_store.upsert_points.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_new_document_success(
    staged_upload,
    mock_vector_store,
    mock_embedding_service,
    mock_ingestion_service,
):
    """Verify clean end-to-end ingestion creates version 1 and indexes into Qdrant."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    # Query 1: duplicate check returns None
    # Query 2: version check returns None (new doc)
    res_dup = MagicMock()
    res_dup.scalars.return_value.first.return_value = None

    res_ver = MagicMock()
    res_ver.scalar.return_value = None

    mock_db.execute.side_effect = [res_dup, res_ver]

    orchestrator = DocumentIngestionOrchestrator(ingestion_service=mock_ingestion_service)
    doc, action, is_dup = await orchestrator.ingest_document(
        staged=staged_upload,
        db=mock_db,
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )

    assert doc.document_version == 1
    assert doc.status == "completed"
    assert doc.is_active is True
    assert doc.chunk_count == 2
    assert action == "created"
    assert is_dup is False

    mock_embedding_service.embed_batch.assert_called_once()
    mock_vector_store.upsert_points.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_new_version_increments_and_deactivates_old(
    staged_upload,
    mock_vector_store,
    mock_embedding_service,
    mock_ingestion_service,
):
    """Verify that uploading different content with same filename creates version N+1,

    activates new version, deactivates old version, and cleans up old vectors.
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    res_dup = MagicMock()
    res_dup.scalars.return_value.first.return_value = None  # No exact duplicate

    res_ver = MagicMock()
    res_ver.scalar.return_value = 1  # Existing max version is 1

    old_doc = DocumentModel(
        id="old-doc-id",
        original_filename="Handbook.pdf",
        normalized_filename="handbook.pdf",
        file_type="pdf",
        file_size=20,
        content_hash="oldhash123",
        document_version=1,
        status="completed",
        is_active=True,
    )
    res_old = MagicMock()
    res_old.scalars.return_value.all.return_value = [old_doc]

    res_chunk_update = MagicMock()

    res_cleanup_ids = MagicMock()
    res_cleanup_ids.scalars.return_value.all.return_value = ["old-doc-id"]

    mock_db.execute.side_effect = [res_dup, res_ver, res_old, res_chunk_update, res_cleanup_ids]

    orchestrator = DocumentIngestionOrchestrator(ingestion_service=mock_ingestion_service)
    doc, action, is_dup = await orchestrator.ingest_document(
        staged=staged_upload,
        db=mock_db,
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )

    assert doc.document_version == 2
    assert doc.is_active is True
    assert action == "version_incremented"
    assert old_doc.is_active is False

    # Verify old vectors were cleaned up from Qdrant
    mock_vector_store.delete_by_document_id.assert_called_with(
        collection_name=orchestrator._settings.QDRANT_COLLECTION_NAME,
        document_id="old-doc-id",
    )


@pytest.mark.asyncio
async def test_ingest_failure_triggers_rollback_and_failed_state(
    staged_upload,
    mock_vector_store,
    mock_embedding_service,
    mock_ingestion_service,
):
    """Verify that an error during vector upsert marks document failed and rolls back vectors."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    res_dup = MagicMock()
    res_dup.scalars.return_value.first.return_value = None
    res_ver = MagicMock()
    res_ver.scalar.return_value = None
    mock_db.execute.side_effect = [res_dup, res_ver]

    # Simulate Qdrant upsert failure
    mock_vector_store.upsert_points.side_effect = Exception("Qdrant connection dropped midway")

    orchestrator = DocumentIngestionOrchestrator(ingestion_service=mock_ingestion_service)

    with pytest.raises(DocumentIngestionFailedError) as exc_info:
        await orchestrator.ingest_document(
            staged=staged_upload,
            db=mock_db,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )

    assert "Qdrant connection dropped" in str(exc_info.value)
    # Verify compensating delete was called
    mock_vector_store.delete_by_document_id.assert_called()


@pytest.mark.asyncio
async def test_retry_completed_document_raises_error(
    staged_upload,
    mock_vector_store,
    mock_embedding_service,
):
    """Verify that attempting to retry an already completed document raises InvalidDocumentStateError."""
    completed_doc = DocumentModel(
        id="doc-already-done",
        original_filename="Handbook.pdf",
        normalized_filename="handbook.pdf",
        file_type="pdf",
        file_size=23,
        content_hash="abc123hash",
        document_version=1,
        status="completed",
        is_active=True,
    )
    mock_db = AsyncMock()
    res = MagicMock()
    res.scalars.return_value.first.return_value = completed_doc
    mock_db.execute.return_value = res

    orchestrator = DocumentIngestionOrchestrator()

    with pytest.raises(InvalidDocumentStateError) as exc_info:
        await orchestrator.retry_failed_document(
            document_id="doc-already-done",
            staged=staged_upload,
            db=mock_db,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )

    assert "already completed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_document_and_vectors_success(
    mock_vector_store,
):
    """Verify that deleting a document purges all versions from Qdrant and Supabase."""
    v1 = DocumentModel(
        id="v1-id",
        original_filename="Policy.pdf",
        normalized_filename="policy.pdf",
        file_type="pdf",
        file_size=10,
        content_hash="h1",
        document_version=1,
        status="completed",
        is_active=False,
    )
    v2 = DocumentModel(
        id="v2-id",
        original_filename="Policy.pdf",
        normalized_filename="policy.pdf",
        file_type="pdf",
        file_size=12,
        content_hash="h2",
        document_version=2,
        status="completed",
        is_active=True,
    )

    mock_db = AsyncMock()
    res_target = MagicMock()
    res_target.scalars.return_value.first.return_value = v2
    res_all = MagicMock()
    res_all.scalars.return_value.all.return_value = [v1, v2]
    mock_db.execute.side_effect = [res_target, res_all]

    orchestrator = DocumentIngestionOrchestrator()
    doc_id, versions, vectors_deleted = await orchestrator.delete_document_and_vectors(
        document_id="v2-id",
        db=mock_db,
        vector_store=mock_vector_store,
    )

    assert doc_id == "v2-id"
    assert versions == [1, 2]
    assert vectors_deleted is True

    # Vector store delete called for both versions
    assert mock_vector_store.delete_by_document_id.call_count == 2
    # Supabase delete called for both records
    assert mock_db.delete.call_count == 2
    mock_db.commit.assert_called_once()
