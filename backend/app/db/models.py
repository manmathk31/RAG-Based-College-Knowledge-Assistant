"""SQLAlchemy ORM models for document metadata persistence in Supabase PostgreSQL."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentModel(Base):
    """Authoritative document registry and metadata model stored in Supabase PostgreSQL."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Stable document identifier (UUID string)",
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original uploaded filename with extension",
    )
    normalized_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Sanitized lowercased filename for grouping document versions",
    )
    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Document format: 'pdf' or 'docx'",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        doc="Document file size in bytes",
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hexadecimal hash of original file content",
    )
    document_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Monotonically increasing version number for this normalized filename",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        doc="Processing status: 'queued', 'processing', 'completed', 'failed'",
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of structured chunks indexed into Qdrant",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if this is the currently active version for user retrieval",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        doc="Timestamp when document record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        doc="Timestamp when document record was last updated",
    )
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when extraction and chunking commenced",
    )
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when ingestion reached completed or failed terminal state",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Safe error diagnostic message if status is failed",
    )

    __table_args__ = (
        UniqueConstraint(
            "normalized_filename",
            "document_version",
            name="uq_documents_filename_version",
        ),
        Index("ix_documents_content_hash", "content_hash"),
        Index("ix_documents_normalized_filename", "normalized_filename"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentModel(id='{self.id}', filename='{self.original_filename}', "
            f"version={self.document_version}, status='{self.status}', is_active={self.is_active})>"
        )


class DocumentChunkModel(Base):
    """PostgreSQL keyword search index for chunks using TSVECTOR and GIN index.

    The canonical chunk text resides in Qdrant Cloud; this model indexes search vectors
    and metadata for fast PostgreSQL Full-Text Search.
    """

    __tablename__ = "document_chunks"

    chunk_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        doc="Stable chunk identifier matching Qdrant point payload",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to parent document in documents table",
    )
    document_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Document version number",
    )
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="1-based page number where chunk originated",
    )
    section_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Section heading associated with chunk",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="True if parent document is currently active",
    )
    search_vector = mapped_column(
        TSVECTOR().with_variant(Text, "sqlite"),
        nullable=False,
        doc="PostgreSQL tsvector generated from chunk content for FTS",
    )

    __table_args__ = (
        Index("ix_document_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_document_chunks_doc_active", "document_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunkModel(chunk_id='{self.chunk_id}', document_id='{self.document_id}', is_active={self.is_active})>"


