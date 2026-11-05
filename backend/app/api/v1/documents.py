"""Document management endpoints for administrators: upload, list, retrieve, retry, and delete."""

import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import desc, func, select
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
from app.db.models import DocumentModel
from app.db.session import get_db
from app.embeddings.base import BaseEmbeddingService
from app.ingestion.orchestrator import DocumentIngestionOrchestrator
from app.schemas.document import (
    DocumentCreateResponse,
    DocumentDeleteResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentRetryResponse,
)
from app.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_admin_secret(
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify that request contains the valid administrative API secret."""
    if not x_admin_secret or x_admin_secret.strip() != settings.ADMIN_API_SECRET.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-Admin-Secret header.",
        )
    return x_admin_secret


def get_orchestrator(request: Request) -> DocumentIngestionOrchestrator:
    """FastAPI dependency for document ingestion orchestrator."""
    if not hasattr(request.app.state, "orchestrator"):
        request.app.state.orchestrator = DocumentIngestionOrchestrator(
            settings=request.app.state.settings if hasattr(request.app.state, "settings") else None,
            ingestion_service=getattr(request.app.state, "ingestion_service", None),
        )
    return request.app.state.orchestrator


def get_vector_store(request: Request) -> BaseVectorStore:
    """FastAPI dependency for vector store adapter."""
    return getattr(request.app.state, "vector_store", None)


def get_embedding_service(request: Request) -> BaseEmbeddingService:
    """FastAPI dependency for embedding service."""
    return getattr(request.app.state, "embedding_service", None)


@router.post(
    "",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a college document",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF or DOCX file to upload and ingest"),
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
    orchestrator: DocumentIngestionOrchestrator = Depends(get_orchestrator),
    vector_store: BaseVectorStore = Depends(get_vector_store),
    embedding_service: BaseEmbeddingService = Depends(get_embedding_service),
) -> DocumentCreateResponse:
    """Upload a document, validate signature and size, extract and chunk content,

    compute embeddings, index vectors in Qdrant, and register in Supabase.
    """
    staged = None
    try:
        staged = await orchestrator.stage_and_validate_upload(file)

        doc, action, is_dup = await orchestrator.ingest_document(
            staged=staged,
            db=db,
            vector_store=vector_store,
            embedding_service=embedding_service,
        )

        msg = (
            f"Document '{doc.original_filename}' successfully processed."
            if not is_dup
            else f"Document '{doc.original_filename}' already indexed (exact duplicate skipped)."
        )

        return DocumentCreateResponse(
            message=msg,
            action=action,
            is_duplicate=is_dup,
            document=DocumentDetailResponse.model_validate(doc),
        )

    except UnsupportedFileFormatError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    except FileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except DocumentIngestionFailedError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    finally:
        if staged:
            staged.cleanup()


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List uploaded documents with pagination and status filters",
)
async def list_documents(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Items per page limit"),
    doc_status: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. completed, failed)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """Retrieve a paginated list of documents with optional status and active filters."""
    query = select(DocumentModel)

    if doc_status:
        query = query.where(DocumentModel.status == doc_status)
    if is_active is not None:
        query = query.where(DocumentModel.is_active == is_active)

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_stmt)
    total = count_res.scalar() or 0

    # Fetch items
    query = query.order_by(desc(DocumentModel.created_at)).offset(skip).limit(limit)
    res = await db.execute(query)
    items = res.scalars().all()

    return DocumentListResponse(
        items=[DocumentDetailResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Retrieve document metadata and processing status",
)
async def get_document(
    document_id: str,
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Retrieve detailed metadata and processing lifecycle status for a single document."""
    stmt = select(DocumentModel).where(DocumentModel.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    return DocumentDetailResponse.model_validate(doc)


@router.post(
    "/{document_id}/retry",
    response_model=DocumentRetryResponse,
    summary="Retry a failed document ingestion",
)
async def retry_document(
    document_id: str,
    file: UploadFile = File(..., description="Original PDF or DOCX file to retry"),
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
    orchestrator: DocumentIngestionOrchestrator = Depends(get_orchestrator),
    vector_store: BaseVectorStore = Depends(get_vector_store),
    embedding_service: BaseEmbeddingService = Depends(get_embedding_service),
) -> DocumentRetryResponse:
    """Retry a previously failed document by supplying the original file again."""
    staged = None
    try:
        staged = await orchestrator.stage_and_validate_upload(file)

        updated_doc = await orchestrator.retry_failed_document(
            document_id=document_id,
            staged=staged,
            db=db,
            vector_store=vector_store,
            embedding_service=embedding_service,
        )

        return DocumentRetryResponse(
            message=f"Document '{updated_doc.original_filename}' successfully re-ingested.",
            document=DocumentDetailResponse.model_validate(updated_doc),
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidDocumentStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (UnsupportedFileFormatError, FileValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except DocumentIngestionFailedError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    finally:
        if staged:
            staged.cleanup()


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document and its indexed vectors",
)
async def delete_document(
    document_id: str,
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
    orchestrator: DocumentIngestionOrchestrator = Depends(get_orchestrator),
    vector_store: BaseVectorStore = Depends(get_vector_store),
) -> DocumentDeleteResponse:
    """Delete a document, all its historical versions, and purge indexed vectors from Qdrant."""
    try:
        doc_id, versions, vectors_deleted = await orchestrator.delete_document_and_vectors(
            document_id=document_id,
            db=db,
            vector_store=vector_store,
        )
        return DocumentDeleteResponse(
            message=f"Document '{doc_id}' and all versions successfully deleted.",
            document_id=doc_id,
            deleted_versions=versions,
            vectors_deleted=vectors_deleted,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DocumentIngestionFailedError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
