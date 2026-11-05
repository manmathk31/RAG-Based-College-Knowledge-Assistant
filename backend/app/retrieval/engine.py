"""Hybrid Retrieval Engine coordinating Dense, Keyword, RRF, and Context Assembly."""

import asyncio
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import RetrievalError
from app.embeddings.base import BaseEmbeddingService
from app.retrieval.context import ContextBuilder
from app.retrieval.dense import DenseRetriever
from app.retrieval.keyword import KeywordRetriever
from app.retrieval.models import RetrievalCandidate, SourceCitation
from app.retrieval.rrf import reciprocal_rank_fusion
from app.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)


class HybridRetrievalEngine:
    """Coordinates hybrid retrieval across dense vector search and keyword full-text search,

    applying Reciprocal Rank Fusion and graceful degradation when a provider is unavailable.
    """

    def __init__(
        self,
        embedding_service: BaseEmbeddingService,
        vector_store: BaseVectorStore,
        settings: Optional[Settings] = None,
        context_builder: Optional[ContextBuilder] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._dense_retriever = DenseRetriever(
            embedding_service=embedding_service,
            vector_store=vector_store,
            settings=self._settings,
        )
        self._keyword_retriever = KeywordRetriever(
            vector_store=vector_store,
            settings=self._settings,
        )
        self._context_builder = context_builder or ContextBuilder(settings=self._settings)

    async def retrieve_and_build_context(
        self,
        query: str,
        db: Optional[AsyncSession] = None,
        top_k: Optional[int] = None,
        max_context_tokens: Optional[int] = None,
    ) -> Tuple[str, List[SourceCitation], str, List[RetrievalCandidate]]:
        """Execute hybrid search, apply RRF, and build prompt context.

        Args:
            query: Natural language question from user.
            db: Optional database session for keyword search.
            top_k: Final top candidates to fuse.
            max_context_tokens: Token budget for prompt context.

        Returns:
            Tuple of (formatted_context, source_citations, retrieval_mode, final_candidates).
        """
        k_val = top_k or self._settings.RETRIEVAL_TOP_K
        dense_limit = self._settings.RETRIEVAL_DENSE_CANDIDATES
        keyword_limit = self._settings.RETRIEVAL_KEYWORD_CANDIDATES

        dense_candidates: List[RetrievalCandidate] = []
        keyword_candidates: List[RetrievalCandidate] = []
        dense_error = None
        keyword_error = None

        # Execute dense and keyword in parallel if db session is present
        if db is not None:
            dense_task = self._dense_retriever.retrieve(query, limit=dense_limit)
            keyword_task = self._keyword_retriever.retrieve(query, db=db, limit=keyword_limit)

            results = await asyncio.gather(dense_task, keyword_task, return_exceptions=True)
            if isinstance(results[0], Exception):
                dense_error = results[0]
                logger.warning("Dense retrieval error in hybrid engine: %s", dense_error)
            else:
                dense_candidates = results[0]

            if isinstance(results[1], Exception):
                keyword_error = results[1]
                logger.warning("Keyword retrieval error in hybrid engine: %s", keyword_error)
            else:
                keyword_candidates = results[1]
        else:
            # PostgreSQL unavailable / unconfigured; run dense search only
            try:
                dense_candidates = await self._dense_retriever.retrieve(query, limit=dense_limit)
            except Exception as exc:
                dense_error = exc
                logger.warning("Dense retrieval failed: %s", exc)

        # Determine retrieval mode and handle degradation
        if dense_error and (keyword_error or db is None or not keyword_candidates):
            raise RetrievalError(
                f"Both dense vector retrieval and keyword retrieval failed. Dense: {dense_error}, Keyword: {keyword_error}"
            )

        if dense_candidates and keyword_candidates:
            retrieval_mode = "hybrid"
            fused = reciprocal_rank_fusion(
                dense_candidates=dense_candidates,
                keyword_candidates=keyword_candidates,
                k=self._settings.RRF_K,
                top_k=k_val,
            )
        elif dense_candidates:
            retrieval_mode = "dense_only"
            fused = dense_candidates[:k_val]
        elif keyword_candidates:
            retrieval_mode = "keyword_only"
            fused = keyword_candidates[:k_val]
        else:
            retrieval_mode = "none"
            fused = []

        # Build formatted context and source citations
        context_text, citations = self._context_builder.build_context(
            candidates=fused,
            max_tokens=max_context_tokens or self._settings.MAX_CONTEXT_TOKENS,
        )

        return context_text, citations, retrieval_mode, fused

