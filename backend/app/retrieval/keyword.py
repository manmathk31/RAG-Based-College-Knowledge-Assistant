"""PostgreSQL Full-Text Search keyword retrieval using tsvector, GIN index, and ts_rank_cd."""

import logging
import re
from typing import Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import KeywordRetrievalError
from app.db.models import DocumentChunkModel, DocumentModel
from app.retrieval.models import RetrievalCandidate
from app.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)


class KeywordRetriever:
    """Executes keyword search against Supabase PostgreSQL using tsvector and GIN index.

    Retrieves matching chunk IDs and retrieves canonical text from Qdrant.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        settings: Optional[Settings] = None,
    ) -> None:
        self._vector_store = vector_store
        self._settings = settings or get_settings()

    async def retrieve(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 10,
    ) -> List[RetrievalCandidate]:
        """Execute PostgreSQL full-text search with active-version filtering.

        Args:
            query: User's raw question string.
            db: Active async SQLAlchemy session.
            limit: Maximum candidate chunks to return.

        Returns:
            List of ranked RetrievalCandidate objects.
        """
        clean_query = query.strip()
        # Fast exit if query contains no alphanumeric search terms
        if not re.search(r"\w+", clean_query):
            return []

        try:
            # Construct safe tsquery using websearch_to_tsquery
            ts_query = func.websearch_to_tsquery("english", clean_query)
            rank_col = func.ts_rank_cd(DocumentChunkModel.search_vector, ts_query).label("rank_score")

            stmt = (
                select(
                    DocumentChunkModel.chunk_id,
                    DocumentChunkModel.document_id,
                    DocumentChunkModel.document_version,
                    DocumentChunkModel.page_number,
                    DocumentChunkModel.section_title,
                    DocumentModel.original_filename,
                    rank_col,
                )
                .join(DocumentModel, DocumentModel.id == DocumentChunkModel.document_id)
                .where(
                    DocumentChunkModel.is_active.is_(True),
                    DocumentModel.is_active.is_(True),
                    DocumentChunkModel.search_vector.op("@@")(ts_query),
                )
                .order_by(desc(rank_col))
                .limit(limit)
            )

            result = await db.execute(stmt)
            rows = result.all()

            if not rows:
                logger.debug("Keyword search returned 0 rows for query: '%s'", clean_query[:40])
                return []

            # Retrieve canonical text contents from Qdrant
            chunk_ids = [r.chunk_id for r in rows]
            collection_name = self._settings.QDRANT_COLLECTION_NAME

            qdrant_points: Dict[str, Dict] = {}
            try:
                points = await self._vector_store.get_points_by_ids(
                    collection_name=collection_name,
                    point_ids=chunk_ids,
                )
                for pt in points:
                    payload = pt.get("payload", {})
                    cid = payload.get("chunk_id", str(pt.get("id")))
                    qdrant_points[cid] = payload
            except Exception as q_exc:
                logger.warning("Could not fetch canonical chunk text from Qdrant: %s", q_exc)

            # Assemble candidates
            candidates: List[RetrievalCandidate] = []
            for rank, row in enumerate(rows, start=1):
                payload = qdrant_points.get(row.chunk_id, {})
                content = payload.get("content", "")

                candidates.append(
                    RetrievalCandidate(
                        chunk_id=row.chunk_id,
                        document_id=row.document_id,
                        document_name=row.original_filename or payload.get("document_name", "Unknown"),
                        document_version=row.document_version,
                        page_number=row.page_number or payload.get("page_number"),
                        section=row.section_title or payload.get("section") or payload.get("section_heading"),
                        content=content,
                        score=float(row.rank_score),
                        rank=rank,
                        retrieval_source="keyword",
                        metadata=payload,
                    )
                )

            logger.debug("Keyword retrieval returned %d candidates for query: '%s'", len(candidates), clean_query[:40])
            return candidates

        except Exception as exc:
            logger.error("PostgreSQL keyword search failed: %s", exc)
            raise KeywordRetrievalError(f"PostgreSQL keyword search failed: {exc}") from exc

