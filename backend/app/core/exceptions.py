"""Application domain exceptions for embeddings, vector storage, and core services."""


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

