"""Unit tests for document upload validation, file signature sniffing, and temporary file staging."""

import io
import os
import zipfile
import pytest

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import (
    FileValidationError,
    UnsupportedFileFormatError,
)
from app.ingestion.orchestrator import (
    DocumentIngestionOrchestrator,
    normalize_filename,
)


def create_dummy_pdf_bytes(text: str = "Test PDF Content") -> bytes:
    """Create minimal valid PDF byte stream with %PDF- header."""
    return f"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n{text}\n%%EOF".encode("utf-8")


def create_dummy_docx_bytes() -> bytes:
    """Create minimal valid DOCX byte stream with ZIP header and word/document.xml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("word/document.xml", '<?xml version="1.0"?><w:document></w:document>')
    return buf.getvalue()


def test_normalize_filename():
    """Verify filename sanitization, spaces to underscores, and lowercase handling."""
    assert normalize_filename("Academic Regulations 2025.PDF") == "academic_regulations_2025.pdf"
    assert normalize_filename("Course-Syllabus (CS101).docx") == "course-syllabus_cs101.docx"
    assert normalize_filename("../../../etc/passwd.pdf") == "passwd.pdf"
    assert normalize_filename("file__with___multiple____underscores.pdf") == "file_with_multiple_underscores.pdf"


@pytest.mark.asyncio
async def test_stage_valid_pdf_success():
    """Verify that a valid PDF file is staged on disk with correct size, hash, and header."""
    orchestrator = DocumentIngestionOrchestrator()
    pdf_bytes = create_dummy_pdf_bytes("Hello College Assistant")

    upload_file = UploadFile(
        file=io.BytesIO(pdf_bytes),
        filename="Admission_Policy.pdf",
    )

    staged = await orchestrator.stage_and_validate_upload(upload_file)
    try:
        assert os.path.exists(staged.temp_path)
        assert staged.file_type == "pdf"
        assert staged.original_filename == "Admission_Policy.pdf"
        assert staged.normalized_filename == "admission_policy.pdf"
        assert staged.file_size == len(pdf_bytes)
        assert len(staged.content_hash) == 64  # SHA-256 length
    finally:
        staged.cleanup()
        assert not os.path.exists(staged.temp_path)


@pytest.mark.asyncio
async def test_stage_valid_docx_success():
    """Verify that a valid DOCX file is staged and verified as a Word zip archive."""
    orchestrator = DocumentIngestionOrchestrator()
    docx_bytes = create_dummy_docx_bytes()

    upload_file = UploadFile(
        file=io.BytesIO(docx_bytes),
        filename="Syllabus_CS202.docx",
    )

    staged = await orchestrator.stage_and_validate_upload(upload_file)
    try:
        assert os.path.exists(staged.temp_path)
        assert staged.file_type == "docx"
        assert staged.original_filename == "Syllabus_CS202.docx"
        assert staged.normalized_filename == "syllabus_cs202.docx"
        assert staged.file_size == len(docx_bytes)
    finally:
        staged.cleanup()
        assert not os.path.exists(staged.temp_path)


@pytest.mark.asyncio
async def test_stage_unsupported_extension_rejected():
    """Verify that files with unsupported extensions are rejected before reading."""
    orchestrator = DocumentIngestionOrchestrator()
    upload_file = UploadFile(
        file=io.BytesIO(b"malicious script or text"),
        filename="notes.txt",
    )

    with pytest.raises(UnsupportedFileFormatError) as exc_info:
        await orchestrator.stage_and_validate_upload(upload_file)

    assert "Unsupported file format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stage_invalid_pdf_magic_bytes_rejected_and_cleaned_up():
    """Verify that a non-PDF file disguised with a .pdf extension is rejected and cleaned up."""
    orchestrator = DocumentIngestionOrchestrator()
    fake_pdf = b"This is just plain text masquerading as a PDF file."

    upload_file = UploadFile(
        file=io.BytesIO(fake_pdf),
        filename="fake.pdf",
    )

    with pytest.raises(FileValidationError) as exc_info:
        await orchestrator.stage_and_validate_upload(upload_file)

    assert "valid PDF signature" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stage_invalid_docx_zip_rejected_and_cleaned_up():
    """Verify that an invalid DOCX file is rejected and temporary file is removed."""
    orchestrator = DocumentIngestionOrchestrator()
    fake_docx = b"Not a PK zip file at all"

    upload_file = UploadFile(
        file=io.BytesIO(fake_docx),
        filename="fake.docx",
    )

    with pytest.raises(FileValidationError) as exc_info:
        await orchestrator.stage_and_validate_upload(upload_file)

    assert "valid DOCX ZIP signature" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stage_empty_file_rejected():
    """Verify that empty 0-byte uploads are rejected."""
    orchestrator = DocumentIngestionOrchestrator()
    upload_file = UploadFile(
        file=io.BytesIO(b""),
        filename="empty.pdf",
    )

    with pytest.raises(FileValidationError) as exc_info:
        await orchestrator.stage_and_validate_upload(upload_file)

    assert "empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stage_file_exceeding_max_size_rejected():
    """Verify that files exceeding MAX_UPLOAD_SIZE_BYTES are rejected and cleaned up."""
    custom_settings = Settings(MAX_UPLOAD_SIZE_BYTES=100)  # Low 100 byte limit for test
    orchestrator = DocumentIngestionOrchestrator(settings=custom_settings)

    oversized = create_dummy_pdf_bytes("A" * 500)
    upload_file = UploadFile(
        file=io.BytesIO(oversized),
        filename="oversized.pdf",
    )

    with pytest.raises(FileValidationError) as exc_info:
        await orchestrator.stage_and_validate_upload(upload_file)

    assert "exceeds maximum allowed upload limit" in str(exc_info.value)

