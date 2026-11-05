"""Pydantic schemas for document upload, metadata, list, and lifecycle operations."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    """Base document fields."""

    original_filename: str = Field(description="Original filename uploaded by administrator")
    normalized_filename: str = Field(description="Normalized filename used to group document versions")
    file_type: str = Field(description="Format of document ('pdf' or 'docx')")
    file_size: int = Field(description="Size of document in bytes")
    content_hash: str = Field(description="SHA-256 hexadecimal checksum of file content")
    document_version: int = Field(description="Version number for this normalized filename")
    status: str = Field(description="Processing status: 'queued', 'processing', 'completed', 'failed'")
    chunk_count: int = Field(default=0, description="Total chunks indexed in Qdrant")
    is_active: bool = Field(default=False, description="Whether this version is active for search")


class DocumentDetailResponse(DocumentBase):
    """Detailed document response schema including identifiers and timestamps."""

    id: str = Field(description="Stable UUID document identifier")
    created_at: datetime = Field(description="Document record creation timestamp")
    updated_at: datetime = Field(description="Document record last modified timestamp")
    processing_started_at: Optional[datetime] = Field(default=None, description="Ingestion start timestamp")
    processing_completed_at: Optional[datetime] = Field(default=None, description="Ingestion finish timestamp")
    error_message: Optional[str] = Field(default=None, description="Failure diagnostic message if status=failed")

    model_config = ConfigDict(from_attributes=True)


class DocumentCreateResponse(BaseModel):
    """Response returned upon document upload and ingestion submission."""

    message: str = Field(description="Summary message regarding upload outcome")
    action: str = Field(description="Action taken: 'created', 'duplicate_skipped', or 'version_incremented'")
    is_duplicate: bool = Field(default=False, description="True if an exact duplicate was detected")
    document: DocumentDetailResponse = Field(description="Associated document metadata record")


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: List[DocumentDetailResponse] = Field(description="List of document metadata items")
    total: int = Field(description="Total count of documents matching criteria")
    skip: int = Field(description="Offset pagination skip value")
    limit: int = Field(description="Page size limit")


class DocumentDeleteResponse(BaseModel):
    """Response returned upon document deletion."""

    message: str = Field(description="Deletion outcome message")
    document_id: str = Field(description="Deleted document identifier")
    deleted_versions: List[int] = Field(default_factory=list, description="List of document versions cleaned up")
    vectors_deleted: bool = Field(description="True if associated vectors were removed from Qdrant")


class DocumentRetryResponse(BaseModel):
    """Response returned upon retrying a failed document."""

    message: str = Field(description="Retry outcome message")
    document: DocumentDetailResponse = Field(description="Updated document metadata record")

