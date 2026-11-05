"""Document Ingestion Orchestrator connecting Supabase PostgreSQL, extraction, embeddings, and Qdrant."""

import asyncio
from datetime import datetime, timezone
import hashlib
import logging
import os
import re
import tempfile
from typing import BinaryIO, List, Optional, Set, Tuple
import zipfile

from fastapi import UploadFile
from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DatabaseUnavailableError,
    DocumentIngestionFailedError,
    DocumentNotFoundError,
    EmptyDocumentError,
    FileValidationError,
    InvalidDocumentStateError,
    UnsupportedFileFormatError,
)
from app.db.models import DocumentChunkModel, DocumentModel
from app.embeddings.base import BaseEmbeddingService
from app.ingestion.service import DocumentIngestionService
from app.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".docx"}


class StagedUpload:
    """Encapsulates a validated temporary file upload staged on local disk."""

    def __init__(
        self,
        temp_path: str,
        original_filename: str,
        normalized_filename: str,
        file_type: str,
        file_size: int,
        content_hash: str,
    ) -> None:
        self.temp_path = temp_path
        self.original_filename = original_filename
        self.normalized_filename = normalized_filename
        self.file_type = file_type
        self.file_size = file_size
        self.content_hash = content_hash

    def cleanup(self) -> None:
        """Safely delete the temporary file if it exists."""
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
                logger.debug("Cleaned up temporary upload file: %s", self.temp_path)
            except Exception as exc:
                logger.warning("Error deleting temporary file %s: %s", self.temp_path, exc)


def normalize_filename(filename: str) -> str:
    """Sanitize and normalize a filename for grouping document versions."""
    base = os.path.basename(filename).strip()
    name, ext = os.path.splitext(base)
    # Sanitize characters, lowercase
    clean_name = re.sub(r"[^\w\-\.]", "_", name).lower()
    clean_name = re.sub(r"_+", "_", clean_name).strip("_")
    return f"{clean_name}{ext.lower()}"


class DocumentIngestionOrchestrator:
    """Coordinates end-to-end document upload, validation, Supabase registration,

    chunking, batch embedding, and Qdrant vector indexing.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        ingestion_service: Optional[DocumentIngestionService] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ingestion_service = ingestion_service or DocumentIngestionService(settings=self._settings)
        self._concurrency_semaphore = asyncio.Semaphore(self._settings.INGESTION_MAX_CONCURRENT_JOBS)

    async def stage_and_validate_upload(self, upload_file: UploadFile) -> StagedUpload:
        """Stream uploaded file to a temporary disk location while verifying signature,

        size, and computing SHA-256 content hash. Guaranteed to clean up on error.
        """
        raw_filename = upload_file.filename or "unnamed_document"
        _, ext = os.path.splitext(raw_filename)
        ext_lower = ext.lower()

        if ext_lower not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileFormatError(
                f"Unsupported file format '{ext}'. Only PDF (.pdf) and Word (.docx) files are supported."
            )

        file_type = "pdf" if ext_lower == ".pdf" else "docx"
        normalized = normalize_filename(raw_filename)

        hasher = hashlib.sha256()
        total_size = 0
        max_size = self._settings.MAX_UPLOAD_SIZE_BYTES

        # Create a secure temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=ext_lower, prefix="rag_upload_")
        staged = StagedUpload(
            temp_path=temp_path,
            original_filename=raw_filename,
            normalized_filename=normalized,
            file_type=file_type,
            file_size=0,
            content_hash="",
        )

        try:
            with os.fdopen(temp_fd, "wb") as f_out:
                first_chunk = True
                while chunk := await upload_file.read(64 * 1024):  # 64 KB chunk
                    total_size += len(chunk)
                    if total_size > max_size:
                        raise FileValidationError(
                            f"File size exceeds maximum allowed upload limit of {max_size // (1024 * 1024)} MB."
                        )

                    # Validate file signature / magic bytes on first chunk
                    if first_chunk:
                        first_chunk = False
                        if file_type == "pdf" and not chunk.startswith(b"%PDF-"):
                            raise FileValidationError(
                                "Invalid file format: File does not contain a valid PDF signature (%PDF-)."
                            )
                        elif file_type == "docx" and not chunk.startswith(b"PK\x03\x04"):
                            raise FileValidationError(
                                "Invalid file format: File does not contain a valid DOCX ZIP signature."
                            )

                    hasher.update(chunk)
                    f_out.write(chunk)

            if total_size == 0:
                raise FileValidationError("Uploaded file is empty (0 bytes).")

            # Additional deep check for DOCX structure
            if file_type == "docx":
                if not zipfile.is_zipfile(temp_path):
                    raise FileValidationError("Uploaded Word document is a corrupted or invalid ZIP archive.")
                with zipfile.ZipFile(temp_path, "r") as zf:
                    if "word/document.xml" not in zf.namelist():
                        raise FileValidationError(
                            "Uploaded DOCX archive does not contain the required Word document content."
                        )

            staged.file_size = total_size
            staged.content_hash = hasher.hexdigest()
            return staged

        except Exception:
            staged.cleanup()
            raise

    async def ingest_document(
        self,
        staged: StagedUpload,
        db: AsyncSession,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
    ) -> Tuple[DocumentModel, str, bool]:
        """Execute end-to-end document registration, extraction, embedding, and indexing.

        Returns:
            Tuple of (DocumentModel, action_str, is_duplicate_bool).
        """
        async with self._concurrency_semaphore:
            # 1. Exact duplicate check: Same content hash and completed & active
            stmt_dup = select(DocumentModel).where(
                DocumentModel.content_hash == staged.content_hash,
                DocumentModel.status == "completed",
                DocumentModel.is_active.is_(True),
            )
            result_dup = await db.execute(stmt_dup)
            existing_completed = result_dup.scalars().first()

            if existing_completed:
                logger.info(
                    "Exact duplicate detected for hash=%s (existing document id=%s, name='%s'). Skipping re-indexing.",
                    staged.content_hash,
                    existing_completed.id,
                    existing_completed.original_filename,
                )
                return existing_completed, "duplicate_skipped", True

            # 2. Version resolution for same filename
            stmt_ver = select(func.max(DocumentModel.document_version)).where(
                DocumentModel.normalized_filename == staged.normalized_filename
            )
            result_ver = await db.execute(stmt_ver)
            max_ver = result_ver.scalar()

            if max_ver is None:
                new_version = 1
                action = "created"
            else:
                new_version = max_ver + 1
                action = "version_incremented"

            # 3. Register document in Supabase with 'processing' status
            now_utc = datetime.now(timezone.utc)
            doc = DocumentModel(
                original_filename=staged.original_filename,
                normalized_filename=staged.normalized_filename,
                file_type=staged.file_type,
                file_size=staged.file_size,
                content_hash=staged.content_hash,
                document_version=new_version,
                status="processing",
                chunk_count=0,
                is_active=False,
                processing_started_at=now_utc,
            )
            db.add(doc)
            try:
                await db.commit()
                await db.refresh(doc)
            except Exception as db_exc:
                await db.rollback()
                logger.error("Failed to register document in Supabase: %s", db_exc)
                raise DatabaseUnavailableError(f"Failed to record document metadata in Supabase: {db_exc}") from db_exc

            logger.info(
                "Registered document id=%s ('%s', v%d, action=%s). Commencing ingestion pipeline...",
                doc.id,
                doc.original_filename,
                doc.document_version,
                action,
            )

            # 4. Pipeline Execution: Extraction -> Chunking -> Embeddings -> Qdrant
            points_upserted = False
            try:
                # Extraction & Structure-Aware Chunking
                extracted_doc, chunks = await self._ingestion_service.process_document(
                    file_content=staged.temp_path,
                    filename=staged.original_filename,
                    document_id=doc.id,
                )

                if not chunks:
                    raise EmptyDocumentError(f"Document '{doc.original_filename}' produced 0 chunks.")

                # Batch Embedding Generation
                chunk_contents = [c.content for c in chunks]
                embeddings = await embedding_service.embed_batch(
                    chunk_contents,
                    batch_size=self._settings.EMBEDDING_BATCH_SIZE,
                )

                if len(embeddings) != len(chunks):
                    raise DocumentIngestionFailedError(
                        f"Embedding count ({len(embeddings)}) mismatch with chunk count ({len(chunks)})."
                    )

                # Format points for Qdrant
                qdrant_points = []
                for chunk, emb in zip(chunks, embeddings):
                    payload = chunk.to_qdrant_payload(
                        embedding_model=self._settings.EMBEDDING_MODEL,
                        document_version=str(doc.document_version),
                    )
                    # Include document_id and document_version explicitly in payload
                    payload["document_id"] = doc.id
                    payload["document_version"] = doc.document_version
                    payload["is_active"] = True

                    qdrant_points.append(
                        {
                            "id": chunk.chunk_id,
                            "vector": emb,
                            "payload": payload,
                        }
                    )

                # Qdrant Upsert
                collection_name = self._settings.QDRANT_COLLECTION_NAME
                await vector_store.upsert_points(collection_name=collection_name, points=qdrant_points)
                points_upserted = True

                # Index keyword search vectors in Supabase PostgreSQL
                for chunk in chunks:
                    chunk_rec = DocumentChunkModel(
                        chunk_id=chunk.chunk_id,
                        document_id=doc.id,
                        document_version=doc.document_version,
                        page_number=chunk.page_number,
                        section_title=chunk.section_title,
                        is_active=True,
                        search_vector=func.to_tsvector("english", chunk.content),
                    )
                    db.add(chunk_rec)

                # 5. Pipeline Completion: Mark completed and activate in Supabase
                doc.status = "completed"
                doc.chunk_count = len(chunks)
                doc.is_active = True
                doc.processing_completed_at = datetime.now(timezone.utc)
                doc.error_message = None

                # Deactivate older versions of the same document in Supabase
                if new_version > 1:
                    stmt_old = select(DocumentModel).where(
                        DocumentModel.normalized_filename == doc.normalized_filename,
                        DocumentModel.id != doc.id,
                        DocumentModel.is_active.is_(True),
                    )
                    res_old = await db.execute(stmt_old)
                    old_active_docs = res_old.scalars().all()
                    for old_doc in old_active_docs:
                        old_doc.is_active = False

                    # Deactivate older keyword chunk records
                    stmt_old_chunks = (
                        update(DocumentChunkModel)
                        .where(
                            DocumentChunkModel.document_id.in_(
                                select(DocumentModel.id).where(
                                    DocumentModel.normalized_filename == doc.normalized_filename,
                                    DocumentModel.id != doc.id,
                                )
                            )
                        )
                        .values(is_active=False)
                    )
                    await db.execute(stmt_old_chunks)

                await db.commit()
                await db.refresh(doc)
                logger.info(
                    "Successfully indexed document id=%s ('%s', v%d) with %d chunks (vectors & keyword FTS).",
                    doc.id,
                    doc.original_filename,
                    doc.document_version,
                    doc.chunk_count,
                )

                # 6. Compensating cleanup of old vectors after new version is active
                if new_version > 1:
                    await self._cleanup_replaced_version_vectors(
                        vector_store=vector_store,
                        collection_name=collection_name,
                        db=db,
                        normalized_filename=doc.normalized_filename,
                        current_doc_id=doc.id,
                    )

                return doc, action, False

            except Exception as exc:
                logger.error("Ingestion failed for document id=%s: %s", doc.id, exc)
                # Compensating cleanup: Delete any partially indexed vectors for this doc
                if points_upserted or True:
                    try:
                        await vector_store.delete_by_document_id(
                            collection_name=self._settings.QDRANT_COLLECTION_NAME,
                            document_id=doc.id,
                        )
                    except Exception as rb_exc:
                        logger.warning("Compensating Qdrant rollback failed for doc id=%s: %s", doc.id, rb_exc)

                # Mark as failed in Supabase
                doc.status = "failed"
                doc.is_active = False
                doc.error_message = str(exc)[:1000]
                doc.processing_completed_at = datetime.now(timezone.utc)
                try:
                    await db.commit()
                except Exception as commit_exc:
                    logger.error("Failed to record failure status in Supabase: %s", commit_exc)

                raise DocumentIngestionFailedError(f"Document ingestion failed: {exc}") from exc

    async def _cleanup_replaced_version_vectors(
        self,
        vector_store: BaseVectorStore,
        collection_name: str,
        db: AsyncSession,
        normalized_filename: str,
        current_doc_id: str,
    ) -> None:
        """Remove vectors for superseded document versions from Qdrant."""
        stmt = select(DocumentModel.id).where(
            DocumentModel.normalized_filename == normalized_filename,
            DocumentModel.id != current_doc_id,
        )
        result = await db.execute(stmt)
        old_ids = result.scalars().all()

        for old_id in old_ids:
            try:
                await vector_store.delete_by_document_id(
                    collection_name=collection_name,
                    document_id=old_id,
                )
                logger.info("Cleaned up superseded vectors for document_id=%s from Qdrant.", old_id)
            except Exception as exc:
                logger.warning(
                    "Compensating cleanup: failed to delete old vectors for superseded document_id=%s: %s. "
                    "Record remains inactive in Supabase.",
                    old_id,
                    exc,
                )

    async def retry_failed_document(
        self,
        document_id: str,
        staged: StagedUpload,
        db: AsyncSession,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
    ) -> DocumentModel:
        """Retry a failed document ingestion by re-processing with a newly uploaded file."""
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalars().first()

        if not doc:
            raise DocumentNotFoundError(f"Document with ID '{document_id}' not found.")

        if doc.status == "completed":
            raise InvalidDocumentStateError(
                f"Document '{doc.original_filename}' is already completed. To update it, upload as a new version."
            )

        if doc.normalized_filename != staged.normalized_filename:
            raise FileValidationError(
                f"Uploaded file '{staged.original_filename}' does not match target document filename '{doc.original_filename}'."
            )

        # Update metadata for retry
        doc.status = "processing"
        doc.file_size = staged.file_size
        doc.content_hash = staged.content_hash
        doc.error_message = None
        doc.processing_started_at = datetime.now(timezone.utc)
        doc.processing_completed_at = None
        await db.commit()

        try:
            # Process extraction, embedding, Qdrant
            extracted_doc, chunks = await self._ingestion_service.process_document(
                file_content=staged.temp_path,
                filename=doc.original_filename,
                document_id=doc.id,
            )

            chunk_contents = [c.content for c in chunks]
            embeddings = await embedding_service.embed_batch(
                chunk_contents,
                batch_size=self._settings.EMBEDDING_BATCH_SIZE,
            )

            qdrant_points = []
            for chunk, emb in zip(chunks, embeddings):
                payload = chunk.to_qdrant_payload(
                    embedding_model=self._settings.EMBEDDING_MODEL,
                    document_version=str(doc.document_version),
                )
                payload["document_id"] = doc.id
                payload["document_version"] = doc.document_version
                payload["is_active"] = True

                qdrant_points.append(
                    {
                        "id": chunk.chunk_id,
                        "vector": emb,
                        "payload": payload,
                    }
                )

            await vector_store.upsert_points(
                collection_name=self._settings.QDRANT_COLLECTION_NAME,
                points=qdrant_points,
            )

            # Re-index keyword search vectors in Supabase PostgreSQL
            await db.execute(delete(DocumentChunkModel).where(DocumentChunkModel.document_id == doc.id))
            for chunk in chunks:
                chunk_rec = DocumentChunkModel(
                    chunk_id=chunk.chunk_id,
                    document_id=doc.id,
                    document_version=doc.document_version,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    is_active=True,
                    search_vector=func.to_tsvector("english", chunk.content),
                )
                db.add(chunk_rec)

            doc.status = "completed"
            doc.chunk_count = len(chunks)
            doc.is_active = True
            doc.processing_completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(doc)
            return doc

        except Exception as exc:
            try:
                await vector_store.delete_by_document_id(
                    collection_name=self._settings.QDRANT_COLLECTION_NAME,
                    document_id=doc.id,
                )
            except Exception:
                pass

            try:
                await db.execute(delete(DocumentChunkModel).where(DocumentChunkModel.document_id == doc.id))
            except Exception:
                pass

            doc.status = "failed"
            doc.error_message = str(exc)[:1000]
            doc.processing_completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise DocumentIngestionFailedError(f"Retry ingestion failed: {exc}") from exc

    async def delete_document_and_vectors(
        self,
        document_id: str,
        db: AsyncSession,
        vector_store: BaseVectorStore,
    ) -> Tuple[str, List[int], bool]:
        """Identify a document and its versions, remove vectors from Qdrant, and delete Supabase records."""
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await db.execute(stmt)
        target_doc = result.scalars().first()

        if not target_doc:
            raise DocumentNotFoundError(f"Document with ID '{document_id}' not found.")

        # Find all versions of this document
        stmt_all = select(DocumentModel).where(
            DocumentModel.normalized_filename == target_doc.normalized_filename
        )
        res_all = await db.execute(stmt_all)
        all_versions = res_all.scalars().all()

        deleted_versions = [v.document_version for v in all_versions]
        collection_name = self._settings.QDRANT_COLLECTION_NAME

        # 1. Delete associated vectors from Qdrant for every version
        for v in all_versions:
            try:
                await vector_store.delete_by_document_id(
                    collection_name=collection_name,
                    document_id=v.id,
                )
            except Exception as q_exc:
                logger.error(
                    "Failed to delete Qdrant vectors for doc_id=%s during document deletion: %s",
                    v.id,
                    q_exc,
                )
                # If vector store is unreachable, do not remove DB record to keep audit trail
                raise DocumentIngestionFailedError(
                    f"Failed to remove indexed vectors from Qdrant for version {v.document_version}: {q_exc}"
                ) from q_exc

        # 2. Delete Supabase records
        for v in all_versions:
            await db.delete(v)

        await db.commit()
        logger.info(
            "Successfully deleted document '%s' (versions: %s) and its Qdrant vectors.",
            target_doc.original_filename,
            deleted_versions,
        )
        return document_id, deleted_versions, True

