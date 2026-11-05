"""Document ingestion package: extractors, models, chunker, and processing service."""

from app.ingestion.chunker import StructureAwareChunker
from app.ingestion.extractors.base import BaseExtractor
from app.ingestion.extractors.docx import DOCXExtractor
from app.ingestion.extractors.ocr import TesseractOCRExtractor
from app.ingestion.extractors.pdf import PDFExtractor
from app.ingestion.models import DocumentChunk, ExtractedBlock, ExtractedDocument, ExtractedPage
from app.ingestion.orchestrator import (
    DocumentIngestionOrchestrator,
    StagedUpload,
    normalize_filename,
)
from app.ingestion.service import DocumentIngestionService

__all__ = [
    "BaseExtractor",
    "PDFExtractor",
    "DOCXExtractor",
    "TesseractOCRExtractor",
    "StructureAwareChunker",
    "DocumentChunk",
    "ExtractedBlock",
    "ExtractedDocument",
    "ExtractedPage",
    "DocumentIngestionService",
    "DocumentIngestionOrchestrator",
    "StagedUpload",
    "normalize_filename",
]
