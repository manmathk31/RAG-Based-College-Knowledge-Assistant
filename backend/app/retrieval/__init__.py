"""Retrieval package: dense, keyword, RRF fusion, context builder, and hybrid retrieval engine."""

from app.retrieval.context import ContextBuilder
from app.retrieval.dense import DenseRetriever
from app.retrieval.engine import HybridRetrievalEngine
from app.retrieval.keyword import KeywordRetriever
from app.retrieval.models import RetrievalCandidate, SourceCitation
from app.retrieval.rrf import reciprocal_rank_fusion

__all__ = [
    "RetrievalCandidate",
    "SourceCitation",
    "DenseRetriever",
    "KeywordRetriever",
    "reciprocal_rank_fusion",
    "ContextBuilder",
    "HybridRetrievalEngine",
]
