"""Reciprocal Rank Fusion (RRF) algorithm for fusing dense and keyword retrieval rankings."""

from collections import defaultdict
import logging
from typing import Dict, List, Optional

from app.retrieval.models import RetrievalCandidate

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    dense_candidates: List[RetrievalCandidate],
    keyword_candidates: List[RetrievalCandidate],
    k: int = 60,
    top_k: int = 5,
) -> List[RetrievalCandidate]:
    """Fuse ranked candidate lists from dense vector search and keyword full-text search

    using Reciprocal Rank Fusion (RRF).

    Formula:
        RRF_Score(chunk) = SUM( 1.0 / (k + rank) ) across all systems where chunk appears.

    Args:
        dense_candidates: Ranked candidate chunks from dense semantic search.
        keyword_candidates: Ranked candidate chunks from keyword search.
        k: Smoothing constant (standard default: 60).
        top_k: Maximum number of fused candidates to return.

    Returns:
        List of deduplicated RetrievalCandidate objects sorted by descending fused score.
    """
    fused_scores: Dict[str, float] = defaultdict(float)
    candidate_map: Dict[str, RetrievalCandidate] = {}
    sources_seen: Dict[str, List[str]] = defaultdict(list)

    # 1. Process Dense Rankings
    for rank, cand in enumerate(dense_candidates, start=1):
        cid = cand.chunk_id
        rrf_contrib = 1.0 / (k + rank)
        fused_scores[cid] += rrf_contrib
        sources_seen[cid].append(f"dense(rank={rank})")
        if cid not in candidate_map:
            candidate_map[cid] = cand

    # 2. Process Keyword Rankings
    for rank, cand in enumerate(keyword_candidates, start=1):
        cid = cand.chunk_id
        rrf_contrib = 1.0 / (k + rank)
        fused_scores[cid] += rrf_contrib
        sources_seen[cid].append(f"keyword(rank={rank})")
        if cid not in candidate_map:
            candidate_map[cid] = cand
        elif not candidate_map[cid].content and cand.content:
            # If keyword candidate has content and previous lacked it, prefer full content
            candidate_map[cid].content = cand.content

    # 3. Sort Candidates by Fused RRF Score
    sorted_chunk_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

    fused_candidates: List[RetrievalCandidate] = []
    for rank, cid in enumerate(sorted_chunk_ids[:top_k], start=1):
        base_cand = candidate_map[cid]
        source_desc = "+".join(sources_seen[cid])

        fused_cand = RetrievalCandidate(
            chunk_id=base_cand.chunk_id,
            document_id=base_cand.document_id,
            document_name=base_cand.document_name,
            document_version=base_cand.document_version,
            page_number=base_cand.page_number,
            section=base_cand.section,
            content=base_cand.content,
            score=round(fused_scores[cid], 6),
            rank=rank,
            retrieval_source=source_desc,
            metadata=base_cand.metadata,
        )
        fused_candidates.append(fused_cand)

    logger.debug(
        "RRF fused %d dense and %d keyword candidates into %d final candidates.",
        len(dense_candidates),
        len(keyword_candidates),
        len(fused_candidates),
    )
    return fused_candidates

