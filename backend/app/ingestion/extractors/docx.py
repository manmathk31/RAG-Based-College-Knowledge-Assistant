"""DOCX document extractor using python-docx with heading and table support."""

import io
import logging
from typing import BinaryIO, List, Optional, Union
import uuid

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.core.exceptions import CorruptedDocumentError, EmptyDocumentError
from app.ingestion.extractors.base import BaseExtractor
from app.ingestion.models import ExtractedBlock, ExtractedDocument, ExtractedPage

logger = logging.getLogger(__name__)


class DOCXExtractor(BaseExtractor):
    """Extracts paragraphs, headings, and tables from DOCX documents in exact document order."""

    def supports(self, filename: str) -> bool:
        """Return True if the filename has a .docx extension."""
        return filename.lower().endswith(".docx")

    async def extract(
        self,
        file_content: Union[bytes, BinaryIO, str],
        filename: str,
        document_id: Optional[str] = None,
    ) -> ExtractedDocument:
        """Extract paragraphs, headings, and tables from a DOCX file.

        Args:
            file_content: Raw bytes, file-like binary stream, or filesystem path.
            filename: Original DOCX filename.
            document_id: Optional document ID (generates UUID4 if omitted).

        Returns:
            ExtractedDocument populated with blocks, sections, and metadata.

        Raises:
            CorruptedDocumentError: If the DOCX file is corrupted or not a valid docx.
            EmptyDocumentError: If the DOCX contains no usable text.
        """
        doc_id = document_id or str(uuid.uuid4())
        content_stream = self._get_stream(file_content)

        try:
            doc = docx.Document(content_stream)
        except Exception as exc:
            logger.error("Failed to parse DOCX document '%s': %s", filename, exc)
            raise CorruptedDocumentError(f"DOCX file '{filename}' is corrupted or invalid: {exc}") from exc

        blocks: List[ExtractedBlock] = []
        sections: List[str] = []
        current_section: Optional[str] = None
        full_text_fragments: List[str] = []

        try:
            for child in doc.element.body.iterchildren():
                # Paragraph element (<w:p>)
                if child.tag.endswith("p"):
                    p = Paragraph(child, doc)
                    text = p.text.strip()
                    if not text:
                        continue

                    style_name = p.style.name if p.style else ""
                    is_heading = self._is_heading_style(style_name, text)

                    if is_heading:
                        current_section = text
                        if text not in sections:
                            sections.append(text)

                        blocks.append(
                            ExtractedBlock(
                                text=text,
                                block_type="heading",
                                section_title=text,
                                level=self._extract_heading_level(style_name),
                            )
                        )
                    else:
                        blocks.append(
                            ExtractedBlock(
                                text=text,
                                block_type="paragraph",
                                section_title=current_section,
                            )
                        )
                    full_text_fragments.append(text)

                # Table element (<w:tbl>)
                elif child.tag.endswith("tbl"):
                    tbl = Table(child, doc)
                    table_md = self._format_table_as_markdown(tbl)
                    if table_md.strip():
                        blocks.append(
                            ExtractedBlock(
                                text=table_md,
                                block_type="table",
                                section_title=current_section,
                            )
                        )
                        full_text_fragments.append(table_md)

        except Exception as exc:
            logger.error("Error during block iteration for DOCX '%s': %s", filename, exc)
            raise CorruptedDocumentError(f"Error extracting structural elements from DOCX '{filename}': {exc}") from exc

        total_text = "\n\n".join(full_text_fragments).strip()
        total_chars = len(total_text)

        if total_chars == 0:
            raise EmptyDocumentError(f"DOCX document '{filename}' contains no extractable text.")

        # In DOCX, physical page boundaries are dynamic/pagination-dependent; represent as logical single page (page 1)
        pages = [
            ExtractedPage(
                page_number=1,
                text=total_text,
                is_ocr=False,
                char_count=total_chars,
            )
        ]

        metadata = {
            "format": "DOCX",
            "paragraphs_count": len([b for b in blocks if b.block_type == "paragraph"]),
            "headings_count": len([b for b in blocks if b.block_type == "heading"]),
            "tables_count": len([b for b in blocks if b.block_type == "table"]),
        }

        # Try to extract core document properties
        try:
            core_props = doc.core_properties
            if core_props.title:
                metadata["title"] = core_props.title
            if core_props.author:
                metadata["author"] = core_props.author
        except Exception:
            pass

        return ExtractedDocument(
            document_id=doc_id,
            filename=filename,
            file_type="docx",
            pages=pages,
            blocks=blocks,
            sections=sections,
            total_pages=1,
            total_chars=total_chars,
            metadata=metadata,
            warnings=[],
        )

    @staticmethod
    def _get_stream(file_content: Union[bytes, BinaryIO, str]) -> Union[io.BytesIO, str]:
        """Convert input content to a file-like stream or validated path for docx.Document."""
        if isinstance(file_content, bytes):
            return io.BytesIO(file_content)
        if isinstance(file_content, str):
            return file_content
        if hasattr(file_content, "read"):
            data = file_content.read()
            if isinstance(data, str):
                return io.BytesIO(data.encode("utf-8"))
            return io.BytesIO(data)
        raise ValueError("Unsupported file content format.")

    @staticmethod
    def _is_heading_style(style_name: str, text: str) -> bool:
        """Determine if a paragraph style represents a heading."""
        lower_style = style_name.lower()
        if "heading" in lower_style or lower_style in ["title", "subtitle"]:
            return True
        # Fallback check for numbered short lines like "1. Admission Requirements"
        if len(text) <= 80 and text.split() and text[0].isdigit():
            if len(text) > 2 and text[1] in [".", " ", "-", ")"]:
                return True
        return False

    @staticmethod
    def _extract_heading_level(style_name: str) -> Optional[int]:
        """Extract numeric heading level (e.g. Heading 1 -> 1)."""
        lower = style_name.lower()
        if "heading" in lower:
            for char in lower:
                if char.isdigit():
                    return int(char)
        if lower == "title":
            return 1
        if lower == "subtitle":
            return 2
        return None

    @staticmethod
    def _format_table_as_markdown(table: Table) -> str:
        """Format a python-docx table into clean, structured Markdown."""
        if not table.rows:
            return ""

        rows_data: List[List[str]] = []
        for row in table.rows:
            # Clean cell texts, collapse internal newlines to spaces
            row_cells = [" ".join(cell.text.split()) for cell in row.cells]
            # Avoid duplicate empty cells if any
            if any(c for c in row_cells):
                rows_data.append(row_cells)

        if not rows_data:
            return ""

        # Normalize column counts
        max_cols = max(len(r) for r in rows_data)
        padded_rows = [r + [""] * (max_cols - len(r)) for r in rows_data]

        lines: List[str] = []
        # Header row
        header = padded_rows[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")

        # Data rows
        for row in padded_rows[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

