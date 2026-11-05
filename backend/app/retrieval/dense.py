"""Dense vector retrieval implementation using Hugging Face embeddings and Qdrant Cloud."""

import logging
from typing import List, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import DenseRetrievalError
from app.embeddings.base import BaseEmbeddingService
from app.retrieval.models import RetrievalCandidate
from app.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Retrieves document chunks via dense semantic vector search in Qdrant Cloud."""

    def __init__(
        self,
        embedding_service: BaseEmbeddingService,
        vector_store: BaseVectorStore,
        settings: Optional[Settings] = None,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._settings = settings or get_settings()

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
    ) -> List[RetrievalCandidate]:
        """Embed the query and execute approximate nearest-neighbor search in Qdrant.

        Filters strictly for active document versions (is_active=True).
        """
        if not query or not query.strip():
            return []

        try:
            # 1. Embed query vector
            query_vector = await self._embedding_service.embed_single(query.strip())

            # 2. Vector search in Qdrant with active-version filter
            collection_name = self._settings.QDRANT_COLLECTION_NAME
            filters = {"is_active": True}

            scored_points = await self._vector_store.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                filters=filters,
            )

            # 3. Map to RetrievalCandidate
            candidates: List[RetrievalCandidate] = []
            for rank, pt in enumerate(scored_points, start=1):
                payload = pt.get("payload", {})
                candidates.append(
                    RetrievalCandidate(
                        chunk_id=payload.get("chunk_id", str(pt.get("id"))),
                        document_id=payload.get("document_id", ""),
                        document_name=payload.get("document_name", "Unknown Document"),
                        document_version=payload.get("document_version", 1),
                        page_number=payload.get("page_number"),
                        section=payload.get("section") or payload.get("section_heading"),
                        content=payload.get("content", ""),
                        score=float(pt.get("score", 0.0)),
                        rank=rank,
                        retrieval_source="dense",
                        metadata=payload,
                    )
                )

            logger.debug("Dense retrieval returned %d candidates for query: '%s'", len(candidates), query[:40])
            return candidates

        except Exception as exc:
            logger.error("Dense vector search failed: %s", exc)
            raise DenseRetrievalError(f"Dense vector retrieval failed: {exc}") from exc

