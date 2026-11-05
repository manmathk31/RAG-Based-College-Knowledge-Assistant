"""Unit tests for Supabase PostgreSQL database models, URL normalization, and connectivity handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.base import Base
from app.db.models import DocumentModel
from app.db.session import (
    _prepare_asyncpg_url,
    check_db_connectivity,
    close_db,
    get_db,
    init_db,
)


def test_prepare_asyncpg_url_variants():
    """Verify that postgresql and postgres schemes are converted to postgresql+asyncpg."""
    # Direct postgres://
    url1 = "postgres://user:pass@db.example.supabase.co:5432/postgres"
    assert _prepare_asyncpg_url(url1).startswith("postgresql+asyncpg://")

    # postgresql:// with sslmode=require
    url2 = "postgresql://user:pass@db.example.supabase.co:5432/postgres?sslmode=require"
    prep2 = _prepare_asyncpg_url(url2)
    assert prep2.startswith("postgresql+asyncpg://")
    assert "ssl=require" in prep2
    assert "sslmode=" not in prep2

    # Already postgresql+asyncpg://
    url3 = "postgresql+asyncpg://user:pass@localhost:5432/postgres"
    assert _prepare_asyncpg_url(url3) == url3

    # Empty string
    assert _prepare_asyncpg_url("") == ""


def test_document_model_schema_attributes():
    """Verify DocumentModel columns, types, indexes, and constraints match specification."""
    table = DocumentModel.__table__
    columns = {c.name: c for c in table.columns}

    # Verify column existence and types
    assert isinstance(columns["id"].type, String)
    assert columns["id"].primary_key is True

    assert isinstance(columns["original_filename"].type, String)
    assert columns["original_filename"].nullable is False

    assert isinstance(columns["normalized_filename"].type, String)
    assert columns["normalized_filename"].nullable is False

    assert isinstance(columns["file_type"].type, String)
    assert isinstance(columns["file_size"].type, BigInteger)
    assert isinstance(columns["content_hash"].type, String)
    assert isinstance(columns["document_version"].type, Integer)
    assert isinstance(columns["status"].type, String)
    assert isinstance(columns["chunk_count"].type, Integer)
    assert isinstance(columns["is_active"].type, Boolean)
    assert isinstance(columns["created_at"].type, DateTime)
    assert isinstance(columns["updated_at"].type, DateTime)
    assert isinstance(columns["processing_started_at"].type, DateTime)
    assert isinstance(columns["processing_completed_at"].type, DateTime)
    assert isinstance(columns["error_message"].type, Text)

    # Verify unique constraint on (normalized_filename, document_version)
    uq_names = [uq.name for uq in table.constraints if uq.name]
    assert "uq_documents_filename_version" in uq_names

    # Verify indexes
    idx_names = [idx.name for idx in table.indexes]
    assert "ix_documents_content_hash" in idx_names
    assert "ix_documents_normalized_filename" in idx_names
    assert "ix_documents_status" in idx_names
    assert "ix_documents_is_active" in idx_names


def test_document_model_repr():
    """Verify DocumentModel __repr__ string formatting."""
    doc = DocumentModel(
        id="test-doc-uuid",
        original_filename="Academic_Calendar_2025.pdf",
        normalized_filename="academic_calendar_2025.pdf",
        file_type="pdf",
        file_size=1024,
        content_hash="abc123hash",
        document_version=1,
        status="completed",
        is_active=True,
    )
    repr_str = repr(doc)
    assert "test-doc-uuid" in repr_str
    assert "Academic_Calendar_2025.pdf" in repr_str
    assert "version=1" in repr_str
    assert "is_active=True" in repr_str


@pytest.mark.asyncio
async def test_get_db_unconfigured_raises_unavailable_error():
    """Verify that get_db raises DatabaseUnavailableError when DB is not configured."""
    # Ensure engine and session factory are None
    await close_db()

    with pytest.raises(DatabaseUnavailableError) as exc_info:
        async for _ in get_db():
            pass

    assert "unavailable or not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_check_db_connectivity_unconfigured_returns_false():
    """Verify that check_db_connectivity returns False cleanly when engine is None."""
    await close_db()
    connected = await check_db_connectivity()
    assert connected is False


@pytest.mark.asyncio
async def test_check_db_connectivity_failure_handled_gracefully():
    """Verify that connection failure returns False without raising an exception."""
    mock_engine = MagicMock()
    mock_connect = MagicMock()
    mock_connect.__aenter__.side_effect = Exception("Simulated network timeout")
    mock_engine.connect.return_value = mock_connect

    with patch("app.db.session._engine", mock_engine):
        connected = await check_db_connectivity()
        assert connected is False

