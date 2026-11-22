"""NLP package for Sentiment Analysis & Information Extraction (NER)."""

from app.nlp.analyzer import (
    CollegeNLPService,
    nlp_service,
    SentimentAnalysisResponse,
    EntityExtractionResponse,
    ExtractedEntity,
    SentimentAspect,
)

__all__ = [
    "CollegeNLPService",
    "nlp_service",
    "SentimentAnalysisResponse",
    "EntityExtractionResponse",
    "ExtractedEntity",
    "SentimentAspect",
]
