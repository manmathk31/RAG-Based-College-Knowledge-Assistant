"""Text embedding services and provider implementations."""

from app.embeddings.base import BaseEmbeddingService
from app.embeddings.huggingface import HuggingFaceEmbeddingService

__all__ = ["BaseEmbeddingService", "HuggingFaceEmbeddingService"]

