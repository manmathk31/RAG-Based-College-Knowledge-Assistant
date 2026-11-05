"""Abstract interface for vector database storage and similarity search."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseVectorStore(ABC):
    """Abstract contract for vector database providers."""

    @abstractmethod
    async def create_collection_if_not_exists(self, collection_name: str, vector_size: int) -> None:
        """Initialize or verify the target vector collection with Cosine distance."""
        pass

    @abstractmethod
    async def validate_collection(self, collection_name: str, expected_vector_size: int) -> bool:
        """Validate that an existing collection matches expected vector configuration."""
        pass

    @abstractmethod
    async def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
    ) -> bool:
        """Upsert embeddings and metadata payloads into the collection.

        Args:
            collection_name: Target Qdrant collection.
            points: List of dicts, each with 'id' (optional), 'vector' (List[float]),
                    and 'payload' (metadata dict).
        """
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform nearest-neighbor vector search.

        Returns:
            List of dicts with 'id', 'score', and 'payload'.
        """
        pass

    @abstractmethod
    async def delete_by_document_id(self, collection_name: str, document_id: str) -> bool:
        """Delete all vectors/points associated with a given document_id."""
        pass

    @abstractmethod
    async def get_points_by_ids(
        self,
        collection_name: str,
        point_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Retrieve points and payloads by point IDs or chunk IDs."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Gracefully release client resources and connections."""
        pass
