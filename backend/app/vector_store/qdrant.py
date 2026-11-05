"""Qdrant Cloud vector database adapter implementing BaseVectorStore."""

import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    CollectionConfigurationMismatchError,
    CollectionNotFoundError,
    VectorStoreConnectionError,
    VectorStoreOperationError,
)
from app.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant Cloud implementation of BaseVectorStore using AsyncQdrantClient."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[AsyncQdrantClient] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._timeout = self._settings.QDRANT_TIMEOUT

        if client:
            self._client = client
            self._owns_client = False
        else:
            url = self._settings.QDRANT_URL.strip() if self._settings.QDRANT_URL else None
            api_key = self._settings.QDRANT_API_KEY.strip() if self._settings.QDRANT_API_KEY else None
            self._client = AsyncQdrantClient(
                url=url,
                api_key=api_key,
                timeout=self._timeout,
            )
            self._owns_client = True

        logger.info("Initialized QdrantVectorStore (configured collection=%s)", self._settings.QDRANT_COLLECTION_NAME)

    @property
    def client(self) -> AsyncQdrantClient:
        """Return the underlying AsyncQdrantClient."""
        return self._client

    async def create_collection_if_not_exists(self, collection_name: str, vector_size: int) -> None:
        """Create collection if it does not exist, or validate existing configuration.

        Args:
            collection_name: Name of target collection.
            vector_size: Dimensionality of vectors (e.g. 384).
        """
        try:
            exists = await self._client.collection_exists(collection_name)
        except Exception as exc:
            logger.error("Failed to check if Qdrant collection '%s' exists: %s", collection_name, exc)
            raise VectorStoreConnectionError(f"Cannot reach Qdrant to check collection '{collection_name}': {exc}") from exc

        if not exists:
            logger.info("Collection '%s' does not exist. Creating with vector size=%d, distance=Cosine...", collection_name, vector_size)
            try:
                await self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                # Create keyword payload index for document_id filtering
                await self._client.create_payload_index(
                    collection_name=collection_name,
                    field_name="document_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                logger.info("Collection '%s' successfully created with payload index on 'document_id'.", collection_name)
            except Exception as exc:
                logger.error("Failed to create collection '%s': %s", collection_name, exc)
                raise VectorStoreOperationError(f"Failed to create collection '{collection_name}': {exc}") from exc
        else:
            logger.info("Collection '%s' already exists. Validating configuration...", collection_name)
            await self.validate_collection(collection_name, vector_size)

    async def validate_collection(self, collection_name: str, expected_vector_size: int) -> bool:
        """Validate that an existing collection has compatible vector size and Cosine distance."""
        try:
            info = await self._client.get_collection(collection_name)
        except Exception as exc:
            logger.error("Failed to fetch info for collection '%s': %s", collection_name, exc)
            raise CollectionNotFoundError(f"Collection '{collection_name}' could not be inspected: {exc}") from exc

        vectors_config = info.config.params.vectors

        if isinstance(vectors_config, models.VectorParams):
            actual_size = vectors_config.size
            actual_distance = vectors_config.distance
        elif isinstance(vectors_config, dict) and "" in vectors_config:
            actual_size = vectors_config[""].size
            actual_distance = vectors_config[""].distance
        else:
            actual_size = None
            actual_distance = None

        if actual_size != expected_vector_size or actual_distance != models.Distance.COSINE:
            err_msg = (
                f"Collection '{collection_name}' configuration mismatch: "
                f"size={actual_size} (expected {expected_vector_size}), "
                f"distance={actual_distance} (expected {models.Distance.COSINE})."
            )
            logger.error(err_msg)
            raise CollectionConfigurationMismatchError(err_msg)

        logger.info("Collection '%s' configuration validated successfully.", collection_name)
        return True

    async def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
    ) -> bool:
        """Upsert a batch of vectors with payload metadata into Qdrant."""
        if not points:
            return True

        point_structs: List[models.PointStruct] = []
        for idx, p in enumerate(points):
            raw_id = p.get("id")
            vector = p.get("vector")
            payload = p.get("payload", {})

            if vector is None or not isinstance(vector, list):
                raise ValueError(f"Point at index {idx} must contain a valid list 'vector'.")

            point_id = self._normalize_point_id(raw_id)
            point_structs.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        try:
            await self._client.upsert(
                collection_name=collection_name,
                points=point_structs,
            )
            logger.debug("Successfully upserted %d points into collection '%s'.", len(point_structs), collection_name)
            return True
        except Exception as exc:
            logger.error("Failed to upsert points into collection '%s': %s", collection_name, exc)
            raise VectorStoreOperationError(f"Failed to upsert points into collection '{collection_name}': {exc}") from exc

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        filters: Optional[Union[Dict[str, Any], models.Filter]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform nearest-neighbor vector search in Qdrant."""
        if not query_vector:
            raise ValueError("query_vector must not be empty.")

        query_filter: Optional[models.Filter] = None
        if isinstance(filters, models.Filter):
            query_filter = filters
        elif isinstance(filters, dict) and filters:
            must_conditions = []
            for key, val in filters.items():
                must_conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=val)))
            query_filter = models.Filter(must=must_conditions)

        try:
            scored_points = await self._client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
            )
        except Exception as exc:
            logger.error("Vector search failed in collection '%s': %s", collection_name, exc)
            raise VectorStoreOperationError(f"Vector search failed in collection '{collection_name}': {exc}") from exc

        return [
            {
                "id": str(pt.id),
                "score": float(pt.score),
                "payload": pt.payload or {},
            }
            for pt in scored_points
        ]

    async def delete_by_document_id(self, collection_name: str, document_id: str) -> bool:
        """Delete all points corresponding to a document_id."""
        if not document_id or not document_id.strip():
            raise ValueError("document_id must be a non-empty string.")

        delete_filter = models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )

        try:
            await self._client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(filter=delete_filter),
            )
            logger.info("Deleted points for document_id='%s' from collection '%s'.", document_id, collection_name)
            return True
        except Exception as exc:
            logger.error("Failed to delete points for document_id='%s' from collection '%s': %s", document_id, collection_name, exc)
            raise VectorStoreOperationError(f"Failed to delete points for document_id '{document_id}': {exc}") from exc

    async def ping(self) -> bool:
        """Check live connectivity to Qdrant without modifying data."""
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:
            logger.warning("Qdrant ping failed: %s", exc)
            return False

    @staticmethod
    def _normalize_point_id(raw_id: Any) -> Union[str, int]:
        """Convert arbitrary ID into a valid Qdrant point ID (int or UUID string)."""
        if isinstance(raw_id, int):
            return raw_id
        if isinstance(raw_id, str):
            try:
                uuid.UUID(raw_id)
                return raw_id
            except ValueError:
                # Deterministically convert string (e.g. chunk_id) to UUID5
                return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id))
        return str(uuid.uuid4())

    async def close(self) -> None:
        """Close Qdrant client connection if owned by this instance."""
        if self._owns_client and hasattr(self._client, "close"):
            try:
                await self._client.close()
                logger.debug("Closed AsyncQdrantClient connection.")
            except Exception as exc:
                logger.warning("Error closing Qdrant client: %s", exc)

