"""Unit tests for Reciprocal Rank Fusion (RRF) algorithm."""

import pytest

from app.retrieval.models import RetrievalCandidate
from app.retrieval.rrf import reciprocal_rank_fusion


def make_candidate(chunk_id: str, content: str = "", score: float = 0.5, rank: int = 1, source: str = "dense"):
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id="doc-1",
        document_name="Regulations.pdf",
        document_version=1,
        page_number=1,
        section="General",
        content=content or f"Content for {chunk_id}",
        score=score,
        rank=rank,
        retrieval_source=source,
    )


def test_rrf_dense_only():
    """Verify RRF rank calculations when only dense candidates are provided."""
    dense = [
        make_candidate("c1", rank=1, source="dense"),
        make_candidate("c2", rank=2, source="dense"),
    ]
    fused = reciprocal_rank_fusion(dense_candidates=dense, keyword_candidates=[], k=60, top_k=5)

    assert len(fused) == 2
    assert fused[0].chunk_id == "c1"
    assert fused[0].score == round(1.0 / 61, 6)
    assert fused[1].chunk_id == "c2"
    assert fused[1].score == round(1.0 / 62, 6)


def test_rrf_shared_chunks_sum_reciprocal_ranks():
    """Verify that chunks present in both dense and keyword results combine scores."""
    dense = [
        make_candidate("shared-1", rank=1, source="dense"),
        make_candidate("dense-only", rank=2, source="dense"),
    ]
    keyword = [
        make_candidate("keyword-only", rank=1, source="keyword"),
        make_candidate("shared-1", rank=2, source="keyword"),
    ]

    # shared-1 score: 1/(60+1) + 1/(60+2) = 0.0163934 + 0.016129 = ~0.032522
    # keyword-only score: 1/(60+1) = 0.016393
    # dense-only score: 1/(60+2) = 0.016129
    fused = reciprocal_rank_fusion(dense_candidates=dense, keyword_candidates=keyword, k=60, top_k=5)

    assert len(fused) == 3
    assert fused[0].chunk_id == "shared-1"
    expected_score = round((1.0 / 61) + (1.0 / 62), 6)
    assert fused[0].score == expected_score
    assert "dense(rank=1)" in fused[0].retrieval_source
    assert "keyword(rank=2)" in fused[0].retrieval_source


def test_rrf_top_k_truncation():
    """Verify that RRF respects the top_k parameter."""
    dense = [make_candidate(f"c{i}", rank=i) for i in range(1, 10)]
    fused = reciprocal_rank_fusion(dense_candidates=dense, keyword_candidates=[], k=60, top_k=3)

    assert len(fused) == 3
    assert fused[0].chunk_id == "c1"
    assert fused[1].chunk_id == "c2"
    assert fused[2].chunk_id == "c3"


def test_rrf_empty_inputs_returns_empty():
    """Verify that empty inputs return an empty list without error."""
    fused = reciprocal_rank_fusion(dense_candidates=[], keyword_candidates=[], k=60, top_k=5)
    assert fused == []

