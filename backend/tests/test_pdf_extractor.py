"""Unit tests for PDF document extraction and selective OCR detection."""

from unittest.mock import MagicMock
import pymupdf
import pytest

from app.core.config import Settings
from app.core.exceptions import CorruptedDocumentError, EmptyDocumentError
from app.ingestion.extractors.ocr import TesseractOCRExtractor
from app.ingestion.extractors.pdf import PDFExtractor


@pytest.fixture
def pdf_settings() -> Settings:
    return Settings(
        OCR_ENABLED=True,
        OCR_MIN_PAGE_CHARS=30,
        OCR_DPI=150,
    )


def create_synthetic_pdf(pages_text: list[str]) -> bytes:
    """Helper to generate a multi-page PDF in-memory using PyMuPDF."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_pdf_multipage_text_and_page_preservation(pdf_settings: Settings) -> None:
    """Verify multi-page PDF extracts text page by page with correct page numbers."""
    pages_content = [
        "Page 1: Welcome to the College of Engineering Academic Regulations 2025.",
        "Page 2: Minimum attendance requirement for all courses is 75 percent.",
        "Page 3: Fee refund policies and deadline dates for semester withdrawal.",
    ]
    pdf_bytes = create_synthetic_pdf(pages_content)

    extractor = PDFExtractor(settings=pdf_settings)
    doc = await extractor.extract(pdf_bytes, filename="regulations.pdf")

    assert doc.filename == "regulations.pdf"
    assert doc.file_type == "pdf"
    assert doc.total_pages == 3
    assert len(doc.pages) == 3

    # Check page 1
    assert doc.pages[0].page_number == 1
    assert "Academic Regulations 2025" in doc.pages[0].text
    assert doc.pages[0].is_ocr is False

    # Check page 2
    assert doc.pages[1].page_number == 2
    assert "75 percent" in doc.pages[1].text

    # Check page 3
    assert doc.pages[2].page_number == 3
    assert "Fee refund policies" in doc.pages[2].text


@pytest.mark.asyncio
async def test_pdf_empty_page_handling(pdf_settings: Settings) -> None:
    """Verify that a multi-page PDF with an empty page handles the empty page without failure."""
    pages_content = [
        "First page has substantive text describing college admissions.",
        "",  # Empty middle page
        "Third page has examination schedule details.",
    ]
    pdf_bytes = create_synthetic_pdf(pages_content)

    # Disable OCR for this test to inspect empty page behavior
    pdf_settings.OCR_ENABLED = False
    extractor = PDFExtractor(settings=pdf_settings)
    doc = await extractor.extract(pdf_bytes, filename="admissions.pdf")

    assert doc.total_pages == 3
    assert doc.pages[1].page_number == 2
    assert doc.pages[1].char_count == 0
    assert doc.pages[1].text == ""


@pytest.mark.asyncio
async def test_pdf_scanned_page_detection_and_ocr_fallback(pdf_settings: Settings) -> None:
    """Verify pages with sparse text trigger selective OCR fallback."""
    # Page 1 has normal text; Page 2 has only 5 characters (< threshold 30)
    pages_content = [
        "Normal digital text on the first page containing enough characters.",
        "Scan",  # Only 4 chars, triggers OCR
    ]
    pdf_bytes = create_synthetic_pdf(pages_content)

    mock_ocr = MagicMock(spec=TesseractOCRExtractor)
    mock_ocr.extract_text_from_image.return_value = "OCR Transcribed Text: Official College Seal and Policy Signature."

    extractor = PDFExtractor(settings=pdf_settings, ocr_extractor=mock_ocr)
    doc = await extractor.extract(pdf_bytes, filename="scanned_test.pdf")

    assert doc.total_pages == 2
    assert doc.pages[0].is_ocr is False
    assert doc.pages[1].is_ocr is True
    assert "OCR Transcribed Text" in doc.pages[1].text
    mock_ocr.extract_text_from_image.assert_called_once()


@pytest.mark.asyncio
async def test_pdf_corrupted_file_raises_error(pdf_settings: Settings) -> None:
    """Verify corrupted PDF bytes raise CorruptedDocumentError."""
    corrupted_bytes = b"This is completely invalid PDF header content %PDF-broken"

    extractor = PDFExtractor(settings=pdf_settings)
    with pytest.raises(CorruptedDocumentError, match="corrupted or not a valid PDF"):
        await extractor.extract(corrupted_bytes, filename="corrupted.pdf")


@pytest.mark.asyncio
async def test_pdf_empty_document_raises_error(pdf_settings: Settings) -> None:
    """Verify 0-byte file raises EmptyDocumentError."""
    extractor = PDFExtractor(settings=pdf_settings)
    with pytest.raises(EmptyDocumentError, match="empty"):
        await extractor.extract(b"", filename="empty.pdf")

