"""Abstract base interface for format-specific document extractors."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Union

from app.ingestion.models import ExtractedDocument


class BaseExtractor(ABC):
    """Abstract contract for document extractors (PDF, DOCX, etc.)."""

    @abstractmethod
    def supports(self, filename: str) -> bool:
        """Return True if this extractor supports the given filename/extension."""
        pass

    @abstractmethod
    async def extract(
        self,
        file_content: Union[bytes, BinaryIO, str],
        filename: str,
        document_id: Optional[str] = None,
    ) -> ExtractedDocument:
        """Extract text, pages, sections, and structural blocks from document content.

        Args:
            file_content: Raw bytes, file-like binary stream, or local path.
            filename: Original name of the document file.
            document_id: Optional unique identifier for the document.

        Returns:
            ExtractedDocument instance populated with pages and blocks.
        """
        pass

