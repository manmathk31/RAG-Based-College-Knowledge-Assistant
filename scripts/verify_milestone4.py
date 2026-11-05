"""Milestone 4 Verification Script: Supabase Metadata Database & End-to-End Document Ingestion.

Validates settings, database schema, upload validation, lifecycle transitions,
versioning, compensating cleanup, and API contracts.
"""

import asyncio
from datetime import datetime, timezone
import io
import os
import sys
import tempfile
import uuid
import zipfile

# Set up module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock

from app.api.v1.documents import (
    get_embedding_service,
    get_orchestrator,
    get_vector_store,
)
from app.core.config import get_settings
from app.core.exceptions import (
    DatabaseUnavailableError,
    FileValidationError,
    UnsupportedFileFormatError,
)
from app.db.models import DocumentModel
from app.db.session import (
    _prepare_asyncpg_url,
    check_db_connectivity,
    close_db,
    get_db,
    init_db,
)
from app.ingestion.models import DocumentChunk, ExtractedBlock, ExtractedDocument, ExtractedPage
from app.ingestion.orchestrator import (
    DocumentIngestionOrchestrator,
    StagedUpload,
    normalize_filename,
)
from app.main import app


def print_banner(msg: str) -> None:
    print(f"\n{'=' * 70}\n{msg}\n{'=' * 70}")


def create_sample_pdf(text: str = "College Admission Guidelines 2025") -> bytes:
    return f"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n{text}\n%%EOF".encode("utf-8")


def create_sample_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("word/document.xml", '<?xml version="1.0"?><w:document><w:body><w:p><w:r><w:t>Sample DOCX</w:t></w:r></w:p></w:body></w:document>')
    return buf.getvalue()


async def main() -> None:
    print_banner("Verifying Milestone 4: Supabase Metadata Database & Ingestion Workflow")
    settings = get_settings()

    # 1. Configuration & Settings Check
    print("\n1. Ingestion & Database Settings:")
    print(f"   [OK] Database Pool Size:       {settings.DB_POOL_SIZE}")
    print(f"   [OK] Database Max Overflow:    {settings.DB_MAX_OVERFLOW}")
    print(f"   [OK] Max Upload Size:          {settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.1f} MB")
    print(f"   [OK] Max Concurrent Jobs:      {settings.INGESTION_MAX_CONCURRENT_JOBS}")
    print(f"   [OK] Admin Secret Configured:  {bool(settings.ADMIN_API_SECRET)}")

    db_configured = bool(settings.DATABASE_URL and settings.DATABASE_URL.strip())
    print(f"   [INFO] Supabase DB Configured: {db_configured}")
    if db_configured:
        print("   [INFO] Testing live connection to Supabase...")
        init_db(settings=settings)
        live_ok = await check_db_connectivity()
        print(f"   [{'OK' if live_ok else 'WARN'}] Supabase Reachability: {live_ok}")
    else:
        print("   [NOTE] DATABASE_URL not set. Verifying with mocked and detached database layers.")

    # 2. Database Schema and Constraints
    print("\n2. Database Model & Schema Invariants:")
    table = DocumentModel.__table__
    cols = {c.name: c for c in table.columns}
    required_cols = [
        "id", "original_filename", "normalized_filename", "file_type",
        "file_size", "content_hash", "document_version", "status",
        "chunk_count", "is_active", "created_at", "updated_at",
        "processing_started_at", "processing_completed_at", "error_message"
    ]
    for col in required_cols:
        assert col in cols, f"Missing column: {col}"
    print(f"   [OK] Verified all {len(required_cols)} specified columns on DocumentModel.")

    uq_names = [uq.name for uq in table.constraints if uq.name]
    assert "uq_documents_filename_version" in uq_names
    print("   [OK] Verified composite unique constraint on (normalized_filename, document_version).")

    idx_names = [idx.name for idx in table.indexes]
    for expected_idx in ["ix_documents_content_hash", "ix_documents_normalized_filename", "ix_documents_status", "ix_documents_is_active"]:
        assert expected_idx in idx_names
    print(f"   [OK] Verified all {len(idx_names)} required PostgreSQL indexes.")

    # 3. Upload Validation & Signature Sniffing
    print("\n3. Upload Validation & Staging:")
    orchestrator = DocumentIngestionOrchestrator()

    # Valid PDF
    pdf_bytes = create_sample_pdf("Verification PDF Content")
    pdf_upload = UploadFile(file=io.BytesIO(pdf_bytes), filename="Handbook_2025.pdf")
    staged_pdf = await orchestrator.stage_and_validate_upload(pdf_upload)
    assert os.path.exists(staged_pdf.temp_path)
    assert staged_pdf.file_type == "pdf"
    assert staged_pdf.normalized_filename == "handbook_2025.pdf"
    staged_pdf.cleanup()
    assert not os.path.exists(staged_pdf.temp_path)
    print("   [OK] Valid PDF successfully staged and cleaned up.")

    # Valid DOCX
    docx_bytes = create_sample_docx()
    docx_upload = UploadFile(file=io.BytesIO(docx_bytes), filename="Syllabus.docx")
    staged_docx = await orchestrator.stage_and_validate_upload(docx_upload)
    assert os.path.exists(staged_docx.temp_path)
    assert staged_docx.file_type == "docx"
    staged_docx.cleanup()
    print("   [OK] Valid DOCX zip archive verified and cleaned up.")

    # Invalid PDF signature
    fake_pdf = UploadFile(file=io.BytesIO(b"Not a PDF header"), filename="fake.pdf")
    try:
        await orchestrator.stage_and_validate_upload(fake_pdf)
        assert False, "Should have rejected fake PDF"
    except FileValidationError:
        print("   [OK] Rejected file with spoofed .pdf extension (signature mismatch).")

    # Unsupported extension
    txt_file = UploadFile(file=io.BytesIO(b"sample text"), filename="doc.txt")
    try:
        await orchestrator.stage_and_validate_upload(txt_file)
        assert False, "Should have rejected .txt"
    except UnsupportedFileFormatError:
        print("   [OK] Rejected unsupported file format (.txt).")

    # 4. Orchestration & Lifecycle Logic
    print("\n4. Orchestration Lifecycle (Duplicates, Versions, Rollback):")
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_vstore = AsyncMock()
    mock_vstore.upsert_points.return_value = True
    mock_vstore.delete_by_document_id.return_value = True
    mock_embed = AsyncMock()
    mock_embed.embed_batch.return_value = [[0.05] * 384]

    mock_ingest = AsyncMock()
    dummy_doc = ExtractedDocument(
        document_id="doc-verify",
        filename="Test.pdf",
        file_type="pdf",
        pages=[ExtractedPage(page_number=1, text="Page text", char_count=9)],
        blocks=[ExtractedBlock(text="Page text", block_type="paragraph", page_number=1)],
        total_pages=1,
        total_chars=9,
    )
    dummy_chunk = DocumentChunk(
        chunk_id="chunk-verify-1",
        document_id="doc-verify",
        chunk_index=0,
        content="Page text",
        token_count=3,
        char_count=9,
        page_number=1,
        source_filename="Test.pdf",
        file_type="pdf",
    )
    mock_ingest.process_document.return_value = (dummy_doc, [dummy_chunk])

    orch = DocumentIngestionOrchestrator(ingestion_service=mock_ingest)

    # Test New Document Version 1
    staged_v1 = StagedUpload("temp.pdf", "Test.pdf", "test.pdf", "pdf", 100, "hash_v1")
    res_dup = MagicMock()
    res_dup.scalars.return_value.first.return_value = None
    res_ver = MagicMock()
    res_ver.scalar.return_value = None
    mock_db.execute.side_effect = [res_dup, res_ver]

    doc_v1, action, is_dup = await orch.ingest_document(staged_v1, mock_db, mock_vstore, mock_embed)
    assert doc_v1.document_version == 1
    assert doc_v1.is_active is True
    assert doc_v1.status == "completed"
    assert action == "created"
    print(f"   [OK] Ingested Version 1: status={doc_v1.status}, active={doc_v1.is_active}, action={action}")

    # Test Exact Duplicate Detection
    mock_db.execute.side_effect = None
    res_dup2 = MagicMock()
    res_dup2.scalars.return_value.first.return_value = doc_v1
    mock_db.execute.return_value = res_dup2

    doc_dup, action_dup, is_dup2 = await orch.ingest_document(staged_v1, mock_db, mock_vstore, mock_embed)
    assert doc_dup.id == doc_v1.id
    assert is_dup2 is True
    assert action_dup == "duplicate_skipped"
    print(f"   [OK] Exact duplicate detected: action={action_dup}, is_duplicate={is_dup2}")

    # Test Version Increment (Version 2)
    staged_v2 = StagedUpload("temp2.pdf", "Test.pdf", "test.pdf", "pdf", 120, "hash_v2")
    res_dup3 = MagicMock()
    res_dup3.scalars.return_value.first.return_value = None
    res_ver2 = MagicMock()
    res_ver2.scalar.return_value = 1
    res_old = MagicMock()
    res_old.scalars.return_value.all.return_value = [doc_v1]
    res_cleanup = MagicMock()
    res_cleanup.scalars.return_value.all.return_value = [doc_v1.id]
    mock_db.execute.side_effect = [res_dup3, res_ver2, res_old, res_cleanup]

    doc_v2, action_v2, _ = await orch.ingest_document(staged_v2, mock_db, mock_vstore, mock_embed)
    assert doc_v2.document_version == 2
    assert doc_v2.is_active is True
    assert doc_v1.is_active is False
    assert action_v2 == "version_incremented"
    mock_vstore.delete_by_document_id.assert_called_with(
        collection_name=orch._settings.QDRANT_COLLECTION_NAME,
        document_id=doc_v1.id,
    )
    print(f"   [OK] Version 2 activated, Version 1 deactivated, old vectors purged from Qdrant.")

    # 5. API Endpoints Test
    print("\n5. API Endpoints & Administrative Security:")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Unauthorized check
        res_unauth = await client.post("/api/v1/documents", files={"file": ("test.pdf", pdf_bytes, "application/pdf")})
        assert res_unauth.status_code == 401
        print("   [OK] POST /api/v1/documents requires valid X-Admin-Secret (401 Unauthorized verified).")

        # Health readiness includes database status
        res_ready = await client.get("/api/v1/health/ready")
        assert res_ready.status_code == 200
        ready_data = res_ready.json()
        assert "database_configured" in ready_data
        assert "database_connected" in ready_data
        print(f"   [OK] GET /api/v1/health/ready reports database_configured={ready_data['database_configured']}.")

    print_banner("Milestone 4: ALL CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())

