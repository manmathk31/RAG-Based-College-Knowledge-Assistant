"""High-level document processing service coordinating format extraction and chunking."""

import logging
from typing import BinaryIO, List, Optional, Tuple, Union

from app.core.config import Settings, get_settings
from app.core.exceptions import EmptyDocumentError, UnsupportedFileFormatError
from app.ingestion.chunker import StructureAwareChunker
from app.ingestion.extractors.base import BaseExtractor
from app.ingestion.extractors.docx import DOCXExtractor
from app.ingestion.extractors.pdf import PDFExtractor
from app.ingestion.models import DocumentChunk, ExtractedDocument

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Service coordinating document validation, format-specific extraction, and structure-aware chunking."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        extractors: Optional[List[BaseExtractor]] = None,
        chunker: Optional[StructureAwareChunker] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._chunker = chunker or StructureAwareChunker(settings=self._settings)
        self._extractors = extractors or [
            PDFExtractor(settings=self._settings),
            DOCXExtractor(),
        ]

    def get_extractor_for_file(self, filename: str) -> BaseExtractor:
        """Find an extractor supporting the given file."""
        for extractor in self._extractors:
            if extractor.supports(filename):
                return extractor
        raise UnsupportedFileFormatError(
            f"Unsupported file format for '{filename}'. Only PDF (.pdf) and Word (.docx) files are supported."
        )

    async def process_document(
        self,
        file_content: Union[bytes, BinaryIO, str],
        filename: str,
        document_id: Optional[str] = None,
    ) -> Tuple[ExtractedDocument, List[DocumentChunk]]:
        """Validate, extract, and chunk a document.

        Args:
            file_content: Raw bytes, file stream, or file path.
            filename: Original document filename.
            document_id: Optional unique document identifier.

        Returns:
            Tuple of (ExtractedDocument, List[DocumentChunk]).

        Raises:
            UnsupportedFileFormatError: If file extension is not supported.
            EmptyDocumentError: If document yields no extractable text.
            CorruptedDocumentError: If document is corrupted or unreadable.
        """
        extractor = self.get_extractor_for_file(filename)
        logger.info("Processing document '%s' using %s...", filename, type(extractor).__name__)

        extracted_doc = await extractor.extract(
            file_content=file_content,
            filename=filename,
            document_id=document_id,
        )

        chunks = self._chunker.chunk_document(extracted_doc)

        if not chunks:
            raise EmptyDocumentError(f"Document '{filename}' produced 0 chunks after text extraction.")

        logger.info(
            "Successfully processed '%s': %d pages, %d blocks, %d chunks.",
            filename,
            extracted_doc.total_pages,
            len(extracted_doc.blocks),
            len(chunks),
        )
        return extracted_doc, chunks

