"""Abstract interface for text embedding services."""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingService(ABC):
    """Abstract contract for text embedding generation services."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality produced by the embedding service."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier used for embedding generation."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate an embedding vector for a single text string.

        Args:
            text: Non-empty text string.

        Returns:
            List of floats with length equal to self.dimension.
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of text strings.

        Args:
            texts: List of text strings.

        Returns:
            List of embedding vectors preserving input order.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close client connections and release resources."""
        pass

