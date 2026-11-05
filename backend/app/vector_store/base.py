"""Abstract interface for vector database storage and similarity search."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseVectorStore(ABC):
    """Abstract contract for vector database providers."""

    @abstractmethod
    async def create_collection_if_not_exists(self, collection_name: str, vector_size: int) -> None:
        """Initialize or verify the target vector collection."""
        pass

    @abstractmethod
    async def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
    ) -> bool:
        """Upsert embeddings and metadata payloads into the collection."""
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform nearest-neighbor vector search."""
        pass

