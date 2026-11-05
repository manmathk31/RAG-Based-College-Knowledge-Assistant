"""PDF document extractor using PyMuPDF with selective Tesseract OCR fallback."""

import io
import logging
from typing import BinaryIO, List, Optional, Union
import uuid
from PIL import Image
import pymupdf

from app.core.config import Settings, get_settings
from app.core.exceptions import CorruptedDocumentError, EmptyDocumentError
from app.ingestion.extractors.base import BaseExtractor
from app.ingestion.extractors.ocr import TesseractOCRExtractor
from app.ingestion.models import ExtractedBlock, ExtractedDocument, ExtractedPage

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """Extracts text, structural blocks, and page numbers from PDF files with selective OCR for scanned pages."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        ocr_extractor: Optional[TesseractOCRExtractor] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ocr_enabled = self._settings.OCR_ENABLED
        self._ocr_min_chars = self._settings.OCR_MIN_PAGE_CHARS
        self._ocr_dpi = self._settings.OCR_DPI
        self._ocr_extractor = ocr_extractor or TesseractOCRExtractor(settings=self._settings)

    def supports(self, filename: str) -> bool:
        """Return True if the filename has a .pdf extension."""
        return filename.lower().endswith(".pdf")

    async def extract(
        self,
        file_content: Union[bytes, BinaryIO, str],
        filename: str,
        document_id: Optional[str] = None,
    ) -> ExtractedDocument:
        """Extract pages and structural blocks from a PDF file.

        Args:
            file_content: Raw bytes, file-like binary stream, or filesystem path.
            filename: Original PDF filename.
            document_id: Optional document ID (generates UUID4 if omitted).

        Returns:
            ExtractedDocument containing page-by-page text, blocks, and metadata.

        Raises:
            CorruptedDocumentError: If the PDF stream cannot be opened or parsed.
            EmptyDocumentError: If the PDF contains no extractable text.
        """
        doc_id = document_id or str(uuid.uuid4())
        content_bytes = self._read_bytes(file_content)

        if not content_bytes:
            raise EmptyDocumentError(f"PDF document '{filename}' is empty (0 bytes).")

        try:
            doc = pymupdf.open(stream=content_bytes, filetype="pdf")
        except Exception as exc:
            logger.error("Failed to open PDF document '%s': %s", filename, exc)
            raise CorruptedDocumentError(f"PDF file '{filename}' is corrupted or not a valid PDF: {exc}") from exc

        try:
            total_pages = doc.page_count
            if total_pages == 0:
                raise EmptyDocumentError(f"PDF document '{filename}' contains 0 pages.")

            # Extract outline / Table of Contents if available
            toc_sections: List[str] = []
            try:
                toc = doc.get_toc()
                for item in toc:
                    # item format: [lvl, title, page, ...]
                    if len(item) >= 2 and isinstance(item[1], str) and item[1].strip():
                        toc_sections.append(item[1].strip())
            except Exception as exc:
                logger.debug("Could not read TOC outline from '%s': %s", filename, exc)

            pages: List[ExtractedPage] = []
            blocks: List[ExtractedBlock] = []
            warnings: List[str] = []
            current_section = toc_sections[0] if toc_sections else None

            for page_index in range(total_pages):
                page_number = page_index + 1
                page = doc[page_index]

                # Extract digital selectable text
                page_text = page.get_text("text").strip()
                page_char_count = len(page_text)
                is_ocr = False
                page_warnings: List[str] = []

                # Detect scanned page (insufficient selectable text)
                if page_char_count < self._ocr_min_chars:
                    if self._ocr_enabled:
                        logger.info(
                            "Page %d of '%s' has only %d characters (< threshold %d). Applying selective OCR...",
                            page_number,
                            filename,
                            page_char_count,
                            self._ocr_min_chars,
                        )
                        try:
                            # Render page to high-res image
                            pix = page.get_pixmap(dpi=self._ocr_dpi)
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            ocr_text = self._ocr_extractor.extract_text_from_image(img, page_number=page_number)

                            if ocr_text:
                                page_text = ocr_text
                                page_char_count = len(ocr_text)
                                is_ocr = True
                                page_warnings.append(f"Page {page_number}: selective OCR applied ({page_char_count} chars).")
                            else:
                                page_warnings.append(f"Page {page_number}: OCR produced no text.")
                        except Exception as ocr_exc:
                            logger.warning("OCR failed on page %d of '%s': %s", page_number, filename, ocr_exc)
                            page_warnings.append(f"Page {page_number}: OCR failed ({ocr_exc}).")
                            # If OCR was required because text is zero, propagate or log warning
                            if page_char_count == 0 and total_pages == 1:
                                raise
                    else:
                        page_warnings.append(f"Page {page_number} has sparse text ({page_char_count} chars) and OCR is disabled.")

                # Extract layout blocks for structural chunking
                page_blocks = page.get_text("blocks")
                for blk in page_blocks:
                    # blk: (x0, y0, x1, y1, text, block_no, block_type)
                    if len(blk) >= 7 and blk[6] == 0:  # Text block
                        blk_text = blk[4].strip()
                        if blk_text:
                            is_heading = self._is_likely_heading(blk_text)
                            if is_heading:
                                current_section = blk_text
                                if blk_text not in toc_sections:
                                    toc_sections.append(blk_text)

                            blocks.append(
                                ExtractedBlock(
                                    text=blk_text,
                                    block_type="heading" if is_heading else "paragraph",
                                    page_number=page_number,
                                    section_title=current_section,
                                )
                            )

                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=page_text,
                        is_ocr=is_ocr,
                        char_count=page_char_count,
                        warnings=page_warnings,
                    )
                )
                warnings.extend(page_warnings)

            total_chars = sum(p.char_count for p in pages)
            if total_chars == 0:
                raise EmptyDocumentError(
                    f"PDF document '{filename}' yielded 0 extractable text characters across {total_pages} page(s)."
                )

            metadata = {
                "format": doc.metadata.get("format", "PDF"),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
            }

            return ExtractedDocument(
                document_id=doc_id,
                filename=filename,
                file_type="pdf",
                pages=pages,
                blocks=blocks,
                sections=toc_sections,
                total_pages=total_pages,
                total_chars=total_chars,
                metadata=metadata,
                warnings=warnings,
            )

        finally:
            doc.close()

    @staticmethod
    def _read_bytes(file_content: Union[bytes, BinaryIO, str]) -> bytes:
        """Helper to get raw bytes from bytes, stream, or file path."""
        if isinstance(file_content, bytes):
            return file_content
        if isinstance(file_content, str):
            with open(file_content, "rb") as f:
                return f.read()
        if hasattr(file_content, "read"):
            content = file_content.read()
            if isinstance(content, str):
                return content.encode("utf-8")
            return content
        raise ValueError("Unsupported file content type.")

    @staticmethod
    def _is_likely_heading(text: str) -> bool:
        """Heuristic to detect if a text block represents a section heading."""
        clean = text.strip()
        lines = clean.splitlines()
        # Headings are typically 1-2 lines and <= 80 characters
        if len(lines) <= 2 and len(clean) <= 80:
            if clean.isupper() and len(clean) >= 3:
                return True
            # Matches "1. Intro", "Section 2", "Chapter 3", "Rule 4.1"
            first_word = clean.split()[0].lower() if clean.split() else ""
            if any(first_word.startswith(prefix) for prefix in ["section", "chapter", "part", "rule", "article", "appendix"]):
                return True
            if clean[0].isdigit() and (len(clean) > 2 and clean[1] in [".", " ", "-", ")"]):
                return True
        return False

