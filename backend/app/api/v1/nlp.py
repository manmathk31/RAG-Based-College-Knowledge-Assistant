"""API endpoints for Sentiment Analysis and Information Extraction (CO2 Demonstration)."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.nlp.analyzer import (
    nlp_service,
    SentimentAnalysisResponse,
    EntityExtractionResponse,
)

router = APIRouter()


class TextInputRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000, description="Input text to analyze")


# Pre-loaded curated review samples for instant one-click demonstration
SAMPLE_REVIEWS: List[Dict[str, Any]] = [
    {
        "id": "rev-1",
        "title": "Positive: Academics & Placements",
        "type": "positive",
        "text": "The computer engineering faculty at MITAOE is exceptionally qualified and supportive. Placement drives are conducted very well, with top companies like Veritas and IBM visiting campus and offering packages up to 24 LPA. The digital library is modern and spacious."
    },
    {
        "id": "rev-2",
        "title": "Constructive: Hostel Mess & Administration",
        "type": "negative",
        "text": "The hostel mess food is average and dinner quality is often disappointing. The administrative office is sometimes slow in processing scholarship documents, and the attendance condonation criteria are very strict with 75% minimum requirement."
    },
    {
        "id": "rev-3",
        "title": "Mixed: Infrastructure vs Evaluation",
        "type": "mixed",
        "text": "Campus infrastructure, sports complex and Wi-Fi facilities are great. However, the ESE examination evaluation was quite rigid and the photocopy revaluation fee of Rs. 500 per subject is quite high for students."
    }
]

# Pre-loaded curated policy text samples for instant one-click entity extraction
SAMPLE_POLICIES: List[Dict[str, Any]] = [
    {
        "id": "pol-1",
        "title": "Admissions & Eligibility Regulation",
        "text": "Candidates seeking admission to First Year B.Tech Computer Engineering must have passed 10+2 with at least 45% marks in Physics and Mathematics, along with a non-zero positive score in MHT-CET 2025 or JEE Main. Institutional quota seats are filled strictly on merit."
    },
    {
        "id": "pol-2",
        "title": "Fees Structure & Installment Policy",
        "text": "The interim annual fee approved by the Fee Regulating Authority is Rs. 1,65,000, which includes Tuition Fee of Rs. 1,45,000 and Development Fee of Rs. 20,000. Under the TFWS scheme, eligible students receive 100% tuition waiver. Fees can be paid in 2 equal installments per semester."
    },
    {
        "id": "pol-3",
        "title": "Campus Placements & Dream Offer Guidelines",
        "text": "Students with a minimum CGPA of 6.50 and zero active backlogs can register for campus placements starting in Semester 7. Top recruiters include IBM, Cisco, TCS and Veritas offering packages up to 24 LPA. Students with standard offers below 7 LPA remain eligible for Dream Company drives offering 8 to 15 LPA."
    }
]


@router.post(
    "/sentiment",
    response_model=SentimentAnalysisResponse,
    summary="Analyze sentiment of student feedback or college review",
)
async def analyze_sentiment(payload: TextInputRequest) -> SentimentAnalysisResponse:
    """Classify sentiment (positive, negative, neutral) with aspect breakdown and polarity score."""
    if not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review text cannot be empty."
        )
    return nlp_service.analyze_sentiment(payload.text)


@router.post(
    "/extract-entities",
    response_model=EntityExtractionResponse,
    summary="Extract named college entities (courses, fees, eligibility, dates, placements)",
)
async def extract_entities(payload: TextInputRequest) -> EntityExtractionResponse:
    """Perform Information Extraction (NER) on unstructured college documents or text."""
    if not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text cannot be empty."
        )
    return nlp_service.extract_entities(payload.text)


@router.get(
    "/sample-reviews",
    summary="Get curated sample student reviews for practical demonstration",
)
async def get_sample_reviews():
    """Return pre-configured sample reviews for instant testing."""
    return {"samples": SAMPLE_REVIEWS}


@router.get(
    "/sample-policies",
    summary="Get curated college policy texts for entity extraction demonstration",
)
async def get_sample_policies():
    """Return pre-configured policy texts for instant testing."""
    return {"samples": SAMPLE_POLICIES}
