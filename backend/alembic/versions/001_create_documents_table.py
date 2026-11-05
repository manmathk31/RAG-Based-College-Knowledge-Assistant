"""Create documents metadata table.

Revision ID: 001_create_documents
Revises:
Create Date: 2026-11-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_create_documents"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False, comment="Stable document identifier (UUID)"),
        sa.Column("original_filename", sa.String(length=255), nullable=False, comment="Original uploaded filename with extension"),
        sa.Column("normalized_filename", sa.String(length=255), nullable=False, comment="Sanitized lowercased filename for grouping versions"),
        sa.Column("file_type", sa.String(length=10), nullable=False, comment="Document format ('pdf' or 'docx')"),
        sa.Column("file_size", sa.BigInteger(), nullable=False, comment="File size in bytes"),
        sa.Column("content_hash", sa.String(length=64), nullable=False, comment="SHA-256 hexadecimal hash"),
        sa.Column("document_version", sa.Integer(), nullable=False, server_default="1", comment="Version number"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued", comment="Status: queued, processing, completed, failed"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0", comment="Number of chunks indexed in Qdrant"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Active version flag"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.UniqueConstraint("normalized_filename", "document_version", name="uq_documents_filename_version"),
    )
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"], unique=False)
    op.create_index("ix_documents_normalized_filename", "documents", ["normalized_filename"], unique=False)
    op.create_index("ix_documents_status", "documents", ["status"], unique=False)
    op.create_index("ix_documents_is_active", "documents", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_is_active", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_normalized_filename", table_name="documents")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_table("documents")

