"""Abstract interface for raw document file storage."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class BaseDocumentStorage(ABC):
    """Abstract contract for document persistence to decouple backend from local disk."""

    @abstractmethod
    async def save(self, file_id: str, filename: str, content: BinaryIO) -> str:
        """Save a document artifact and return its storage path or locator."""
        pass

    @abstractmethod
    async def get(self, storage_path: str) -> Optional[bytes]:
        """Retrieve stored document bytes by path."""
        pass

    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """Delete a stored document artifact."""
        pass

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Check if a document exists at storage path."""
        pass

