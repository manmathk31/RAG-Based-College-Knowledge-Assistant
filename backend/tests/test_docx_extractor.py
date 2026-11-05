"""Unit tests for DOCX document extraction including headings and tables."""

import io
import docx
import pytest

from app.core.exceptions import CorruptedDocumentError, EmptyDocumentError
from app.ingestion.extractors.docx import DOCXExtractor


def create_synthetic_docx(include_table: bool = True) -> bytes:
    """Helper to generate a structured DOCX document in-memory."""
    doc = docx.Document()
    doc.add_heading("Academic Regulations 2025", level=1)
    doc.add_paragraph("The Bachelor of Technology program requires 160 credits for graduation.")

    doc.add_heading("Grading System", level=2)
    doc.add_paragraph("Students must maintain a minimum Cumulative Grade Point Average (CGPA) of 5.0.")

    if include_table:
        table = doc.add_table(rows=3, cols=2)
        # Header
        table.cell(0, 0).text = "Grade"
        table.cell(0, 1).text = "Points"
        # Row 1
        table.cell(1, 0).text = "A+"
        table.cell(1, 1).text = "10"
        # Row 2
        table.cell(2, 0).text = "A"
        table.cell(2, 1).text = "9"

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_docx_paragraph_and_heading_extraction() -> None:
    """Verify paragraphs and headings are extracted in document order with section tracking."""
    docx_bytes = create_synthetic_docx(include_table=False)

    extractor = DOCXExtractor()
    doc = await extractor.extract(docx_bytes, filename="handbook.docx")

    assert doc.filename == "handbook.docx"
    assert doc.file_type == "docx"
    assert "Academic Regulations 2025" in doc.sections
    assert "Grading System" in doc.sections

    # Check structural blocks
    heading_blocks = [b for b in doc.blocks if b.block_type == "heading"]
    para_blocks = [b for b in doc.blocks if b.block_type == "paragraph"]

    assert len(heading_blocks) == 2
    assert heading_blocks[0].text == "Academic Regulations 2025"
    assert heading_blocks[1].text == "Grading System"

    assert len(para_blocks) == 2
    assert "160 credits" in para_blocks[0].text
    assert para_blocks[0].section_title == "Academic Regulations 2025"
    assert "CGPA" in para_blocks[1].text
    assert para_blocks[1].section_title == "Grading System"


@pytest.mark.asyncio
async def test_docx_table_extraction() -> None:
    """Verify tables in DOCX are converted into structured Markdown representations."""
    docx_bytes = create_synthetic_docx(include_table=True)

    extractor = DOCXExtractor()
    doc = await extractor.extract(docx_bytes, filename="grades.docx")

    table_blocks = [b for b in doc.blocks if b.block_type == "table"]
    assert len(table_blocks) == 1

    table_text = table_blocks[0].text
    # Markdown table header checks
    assert "| Grade | Points |" in table_text
    assert "| --- | --- |" in table_text
    assert "| A+ | 10 |" in table_text
    assert "| A | 9 |" in table_text


@pytest.mark.asyncio
async def test_docx_empty_document_raises_error() -> None:
    """Verify a DOCX document with no text raises EmptyDocumentError."""
    doc = docx.Document()
    buf = io.BytesIO()
    doc.save(buf)

    extractor = DOCXExtractor()
    with pytest.raises(EmptyDocumentError, match="no extractable text"):
        await extractor.extract(buf.getvalue(), filename="empty.docx")


@pytest.mark.asyncio
async def test_docx_corrupted_file_raises_error() -> None:
    """Verify corrupted non-zip bytes raise CorruptedDocumentError."""
    corrupted_bytes = b"PK\x03\x04corrupted docx content not a valid zip archive"

    extractor = DOCXExtractor()
    with pytest.raises(CorruptedDocumentError, match="corrupted or invalid"):
        await extractor.extract(corrupted_bytes, filename="broken.docx")

