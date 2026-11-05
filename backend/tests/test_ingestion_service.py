"""Unit tests for the integrated DocumentIngestionService coordinating extraction and chunking."""

import io
import docx
import pymupdf
import pytest

from app.core.config import Settings
from app.core.exceptions import EmptyDocumentError, UnsupportedFileFormatError
from app.ingestion.service import DocumentIngestionService


@pytest.fixture
def ingestion_service() -> DocumentIngestionService:
    settings = Settings(
        CHUNK_SIZE=200,
        CHUNK_OVERLAP=40,
        OCR_ENABLED=False,  # Keep OCR disabled for fast synthetic testing
    )
    return DocumentIngestionService(settings=settings)


def create_pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def create_docx_bytes(heading: str, body: str) -> bytes:
    doc = docx.Document()
    doc.add_heading(heading, level=1)
    doc.add_paragraph(body)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_service_process_pdf_end_to_end(ingestion_service: DocumentIngestionService) -> None:
    """Verify processing a valid PDF extracts content and generates DocumentChunks."""
    pdf_bytes = create_pdf_bytes("College of Engineering Exam Attendance Policy requires 75% attendance.")
    extracted_doc, chunks = await ingestion_service.process_document(pdf_bytes, filename="policy.pdf")

    assert extracted_doc.file_type == "pdf"
    assert extracted_doc.total_pages == 1
    assert len(chunks) >= 1
    assert chunks[0].source_filename == "policy.pdf"
    assert chunks[0].page_number == 1
    assert "75% attendance" in chunks[0].content


@pytest.mark.asyncio
async def test_service_process_docx_end_to_end(ingestion_service: DocumentIngestionService) -> None:
    """Verify processing a valid DOCX extracts content and generates DocumentChunks with headings."""
    docx_bytes = create_docx_bytes("Admissions 2025", "Candidate must have passed 12th standard with 60% aggregate.")
    extracted_doc, chunks = await ingestion_service.process_document(docx_bytes, filename="admissions.docx")

    assert extracted_doc.file_type == "docx"
    assert "Admissions 2025" in extracted_doc.sections
    assert len(chunks) >= 1
    assert chunks[0].source_filename == "admissions.docx"
    assert chunks[0].section_title == "Admissions 2025"
    assert "60% aggregate" in chunks[0].content


@pytest.mark.asyncio
async def test_service_unsupported_format_raises_error(ingestion_service: DocumentIngestionService) -> None:
    """Verify non-PDF/non-DOCX file extension raises UnsupportedFileFormatError."""
    with pytest.raises(UnsupportedFileFormatError, match="Unsupported file format"):
        await ingestion_service.process_document(b"plain text content", filename="notes.txt")

    with pytest.raises(UnsupportedFileFormatError, match="Unsupported file format"):
        await ingestion_service.process_document(b"binary data", filename="data.xlsx")

