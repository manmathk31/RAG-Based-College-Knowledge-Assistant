"""Application domain exceptions for embeddings, vector storage, and ingestion."""


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ------------------------------------------------------------------------------
# Embedding Service Exceptions
# ------------------------------------------------------------------------------

class EmbeddingError(AppError):
    """Base exception for embedding generation failures."""
    pass


class EmbeddingDimensionMismatchError(EmbeddingError):
    """Raised when the vector dimension returned by the provider does not match the configured dimension."""
    pass


class EmbeddingRateLimitError(EmbeddingError):
    """Raised when the provider rate limit or quota is exceeded."""
    pass


class EmbeddingTimeoutError(EmbeddingError):
    """Raised when an embedding request times out."""
    pass


class EmbeddingAuthenticationError(EmbeddingError):
    """Raised when provider authentication fails (e.g. invalid or missing token)."""
    pass


class EmbeddingServiceUnavailableError(EmbeddingError):
    """Raised when provider model is temporarily loading or service is unavailable (e.g. HTTP 503)."""
    pass


# ------------------------------------------------------------------------------
# Vector Store Exceptions
# ------------------------------------------------------------------------------

class VectorStoreError(AppError):
    """Base exception for vector database operations."""
    pass


class CollectionNotFoundError(VectorStoreError):
    """Raised when the requested vector collection does not exist."""
    pass


class CollectionConfigurationMismatchError(VectorStoreError):
    """Raised when an existing collection has an incompatible vector size or distance metric."""
    pass


class VectorStoreConnectionError(VectorStoreError):
    """Raised when the vector database cannot be reached."""
    pass


class VectorStoreOperationError(VectorStoreError):
    """Raised when an insert, search, or delete operation fails in the vector store."""
    pass


# ------------------------------------------------------------------------------
# Ingestion & Extraction Exceptions
# ------------------------------------------------------------------------------

class IngestionError(AppError):
    """Base exception for document parsing and ingestion failures."""
    pass


class UnsupportedFileFormatError(IngestionError):
    """Raised when an uploaded document file extension or MIME type is not supported."""
    pass


class CorruptedDocumentError(IngestionError):
    """Raised when an input document file is corrupted or unreadable."""
    pass


class EmptyDocumentError(IngestionError):
    """Raised when an input document yields no extractable text."""
    pass


class OCRError(IngestionError):
    """Raised when optical character recognition fails."""
    pass


class TesseractNotFoundError(OCRError):
    """Raised when Tesseract OCR binary is not installed or not found on PATH."""
    pass


class ChunkingError(IngestionError):
    """Raised when structure-aware chunking fails."""
    pass


# ------------------------------------------------------------------------------
# Relational Database & Document Lifecycle Exceptions
# ------------------------------------------------------------------------------

class DatabaseError(AppError):
    """Base exception for relational database operations."""
    pass


class DatabaseUnavailableError(DatabaseError):
    """Raised when the relational database is not configured or cannot be reached."""
    pass


class DocumentNotFoundError(AppError):
    """Raised when a requested document ID does not exist in the database."""
    pass


class DuplicateDocumentError(AppError):
    """Raised when an exact duplicate document has already been processed."""
    pass


class InvalidDocumentStateError(AppError):
    """Raised when an invalid state transition is attempted on a document."""
    pass


class FileValidationError(AppError):
    """Raised when uploaded file fails magic bytes or size constraints."""
    pass


class DocumentIngestionFailedError(AppError):
    """Raised when document ingestion pipeline fails and triggers compensating rollback."""
    pass


# ------------------------------------------------------------------------------
# Retrieval Exceptions
# ------------------------------------------------------------------------------

class RetrievalError(AppError):
    """Base exception for context retrieval operations."""
    pass


class DenseRetrievalError(RetrievalError):
    """Raised when dense vector search fails in Qdrant."""
    pass


class KeywordRetrievalError(RetrievalError):
    """Raised when PostgreSQL full-text keyword search fails."""
    pass


# ------------------------------------------------------------------------------
# Generation Exceptions (Google Gemini)
# ------------------------------------------------------------------------------

class GenerationError(AppError):
    """Base exception for LLM response generation."""
    pass


class GenerationAuthenticationError(GenerationError):
    """Raised when Gemini API key is missing or invalid."""
    pass


class GenerationRateLimitError(GenerationError):
    """Raised when Gemini quota or rate limits are exceeded."""
    pass


class GenerationTimeoutError(GenerationError):
    """Raised when answer generation request times out."""
    pass


class GenerationServiceUnavailableError(GenerationError):
    """Raised when Gemini service is temporarily unavailable."""
    pass
