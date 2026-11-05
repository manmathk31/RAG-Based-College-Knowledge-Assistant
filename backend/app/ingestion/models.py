"""Pydantic data models for extracted documents and structured chunks."""

import hashlib
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractedBlock(BaseModel):
    """A distinct structural block of text (paragraph, heading, or table cell)."""

    text: str
    block_type: str = "paragraph"  # "paragraph", "heading", "table", "ocr"
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    level: Optional[int] = None  # Heading level (1 for H1, 2 for H2, etc.)


class ExtractedPage(BaseModel):
    """Text and metadata extracted from a single document page."""

    page_number: int  # 1-indexed
    text: str
    is_ocr: bool = False
    char_count: int = 0
    warnings: List[str] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    """Unified internal representation of an extracted document across all supported formats."""

    document_id: str
    filename: str
    file_type: str  # "pdf" or "docx"
    pages: List[ExtractedPage] = Field(default_factory=list)
    blocks: List[ExtractedBlock] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    total_pages: int = 0
    total_chars: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

    def get_full_text(self) -> str:
        """Concatenate all page or block text."""
        if self.pages:
            return "\n\n".join(p.text for p in self.pages if p.text.strip())
        return "\n\n".join(b.text for b in self.blocks if b.text.strip())


class DocumentChunk(BaseModel):
    """A structure-aware chunk ready for embedding and vector database indexing."""

    chunk_id: str  # e.g. "{doc_id}_p{page}_c{index}"
    document_id: str
    chunk_index: int  # 0-indexed sequence position
    content: str
    token_count: int
    char_count: int
    page_number: Optional[int] = None
    page_range: Optional[List[int]] = None
    section_title: Optional[str] = None
    source_filename: str
    file_type: str
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Compute SHA-256 content hash if not provided."""
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def to_qdrant_payload(self, embedding_model: str = "", document_version: str = "1.0") -> Dict[str, Any]:
        """Convert chunk into a payload compatible with Qdrant vector store."""
        return {
            "document_id": self.document_id,
            "document_name": self.source_filename,
            "document_version": document_version,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number or (self.page_range[0] if self.page_range else 1),
            "section": self.section_title or "General",
            "content": self.content,
            "content_hash": self.content_hash,
            "embedding_model": embedding_model,
            "file_type": self.file_type,
            "token_count": self.token_count,
            "char_count": self.char_count,
            "page_range": self.page_range,
            **self.metadata,
        }

