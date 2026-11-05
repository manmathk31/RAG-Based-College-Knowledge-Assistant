"""Create document_chunks keyword search index table with tsvector and GIN index.

Revision ID: 002_create_document_chunks_fts
Revises: 001_create_documents
Create Date: 2026-11-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "002_create_document_chunks_fts"
down_revision: Union[str, None] = "001_create_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("chunk_id", sa.String(length=64), primary_key=True, nullable=False, comment="Stable chunk identifier"),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            comment="Reference to parent document in documents table",
        ),
        sa.Column("document_version", sa.Integer(), nullable=False, server_default="1", comment="Document version number"),
        sa.Column("page_number", sa.Integer(), nullable=True, comment="1-based page number"),
        sa.Column("section_title", sa.String(length=255), nullable=True, comment="Section title or heading"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Active version flag"),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False, comment="PostgreSQL tsvector for keyword FTS"),
    )
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_document_chunks_doc_active",
        "document_chunks",
        ["document_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_doc_active", table_name="document_chunks")
    op.drop_index("ix_document_chunks_search_vector", table_name="document_chunks", postgresql_using="gin")
    op.drop_table("document_chunks")

