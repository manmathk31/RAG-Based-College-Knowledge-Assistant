"""User Chat API endpoints for querying college documents with grounded generation."""

import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DatabaseUnavailableError,
    GenerationAuthenticationError,
    GenerationError,
    GenerationRateLimitError,
    GenerationServiceUnavailableError,
    GenerationTimeoutError,
    RetrievalError,
)
from app.db.session import get_db
from app.generation.base import BaseGenerationService
from app.retrieval.engine import HybridRetrievalEngine
from app.schemas.chat import ChatRequest, ChatResponse
from app.api.v1.auth import get_optional_student
from app.db.auth_models import StudentModel

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_optional_db(request: Request) -> AsyncGenerator[Optional[AsyncSession], None]:
    """Dependency providing an async database session if available, yielding None if unavailable.

    Ensures chat queries continue functioning via dense-only search if Supabase is down.
    """
    gen = None
    try:
        gen = get_db()
        session = await anext(gen)
    except DatabaseUnavailableError:
        logger.info("Supabase PostgreSQL unavailable during chat query; falling back to dense Qdrant retrieval.")
        yield None
        return
    except Exception as exc:
        logger.warning("Database connection failed during chat query (%s); falling back to dense retrieval.", exc)
        yield None
        return

    try:
        yield session
    finally:
        if gen is not None:
            try:
                await gen.aclose()
            except Exception:
                pass


def get_retrieval_engine(request: Request) -> HybridRetrievalEngine:
    """FastAPI dependency for the hybrid retrieval engine."""
    return getattr(request.app.state, "retrieval_engine", None)


def get_generation_service(request: Request) -> BaseGenerationService:
    """FastAPI dependency for the LLM answer generation service."""
    return getattr(request.app.state, "generation_service", None)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the college knowledge assistant",
)
@router.post(
    "/query",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Query alias for frontend compatibility",
)
async def chat_query(
    payload: ChatRequest,
    student: Optional[StudentModel] = Depends(get_optional_student),
    db: Optional[AsyncSession] = Depends(get_optional_db),
    retrieval_engine: HybridRetrievalEngine = Depends(get_retrieval_engine),
    generation_service: BaseGenerationService = Depends(get_generation_service),
) -> ChatResponse:
    """Answer public or student questions by performing hybrid retrieval over college documents

    and generating grounded answers with exact source citations via Google Gemini.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string must not be empty.",
        )

    query_text = payload.message.strip()

    # 1. Hybrid Retrieval and Context Construction
    try:
        context_text, citations, retrieval_mode, _ = await retrieval_engine.retrieve_and_build_context(
            query=query_text,
            db=db,
        )
    except RetrievalError as r_exc:
        logger.error("Context retrieval failed: %s", r_exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Knowledge retrieval service is currently unavailable: {r_exc}",
        )
    except Exception as exc:
        logger.error("Unexpected error in retrieval engine: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving relevant college documents.",
        )

    # 2. Multilingual detection & Honest Fallback if No Context Found
    selected_lang = (payload.language or "en").lower().strip()
    if any("\u0900" <= ch <= "\u097f" for ch in query_text):
        if any(w in query_text for w in ["आहे", "आहेत", "काय", "उपस्थिती", "माहिती", "सांगा", "किती", "नियम", "पाहिजे"]):
            selected_lang = "mr"
        elif any(w in query_text for w in ["क्या", "है", "हैं", "बताएं", "जानकारी", "उपस्थिति", "कितना", "नियम"]):
            selected_lang = "hi"
        elif selected_lang == "en":
            selected_lang = "mr"

    if not citations or not context_text.strip():
        if selected_lang in ["mr", "marathi"]:
            fallback_msg = "मला अधिकृत महाविद्यालयीन कागदपत्रांमध्ये तुमच्या प्रश्नाबद्दल माहिती आढळली नाही."
        elif selected_lang in ["hi", "hindi"]:
            fallback_msg = "मुझे आधिकारिक कॉलेज दस्तावेजों में आपके प्रश्न के संबंध में जानकारी नहीं मिली।"
        else:
            fallback_msg = "I could not find information regarding your question in the official college documents."

        return ChatResponse(
            answer=fallback_msg,
            sources=[],
            retrieval_mode=retrieval_mode,
            language=selected_lang,
            topics=[],
            entities=[],
        )

    # Helper function to enrich response with NLP topics, entities, and optional sentiment
    def enrich_nlp_metadata(answer_text: str):
        from app.nlp.analyzer import nlp_service

        extraction = nlp_service.extract_entities(answer_text)
        extracted_entities = [
            {"text": e.text, "category": e.category, "confidence": round(e.confidence, 2)}
            for e in extraction.entities[:8]
        ]

        # Extract structured topics
        category_labels = {
            "REGULATION": "Academic Regulation",
            "FEE": "Fee Structure & Concession",
            "ELIGIBILITY": "Eligibility & Admission",
            "DATE_DEADLINE": "Important Deadline",
            "COURSE": "Course / Branch",
            "PLACEMENT": "Placement & Career",
            "FACILITY": "Campus Facility & Hostel",
        }
        topics_found = []
        for cat, items in extraction.structured_summary.items():
            if items and cat in category_labels:
                topics_found.append(category_labels[cat])

        # Detect if student inquiry contains feedback/sentiment
        sentiment_data = None
        feedback_triggers = ["mess", "food", "faculty", "hostel", "teacher", "poor", "bad", "terrible", "great", "excellent", "supportive", "rigid"]
        if any(w in query_text.lower() for w in feedback_triggers):
            sent_res = nlp_service.analyze_sentiment(query_text)
            sentiment_data = {
                "overall_sentiment": sent_res.overall_sentiment,
                "polarity_score": round(sent_res.polarity_score, 2),
                "aspects": [a.model_dump() for a in sent_res.aspects],
                "summary": sent_res.summary,
            }

        return topics_found, extracted_entities, sentiment_data

    # 3. Grounded Generation via Gemini
    try:
        history_dicts = [h.model_dump() for h in payload.history] if payload.history else None
        answer = await generation_service.generate_answer(
            query=query_text,
            context_text=context_text,
            history=history_dicts,
            language=selected_lang,
        )

        topics_out, entities_out, sentiment_out = enrich_nlp_metadata(answer)

        return ChatResponse(
            answer=answer,
            sources=citations,
            retrieval_mode=retrieval_mode,
            language=selected_lang,
            topics=topics_out,
            entities=entities_out,
            sentiment=sentiment_out,
        )

    except GenerationAuthenticationError as exc:
        if citations and context_text:
            logger.info("Generating grounded answer from retrieved context using local fallback synthesis (lang=%s).", selected_lang)
            bullet_points = []
            for idx, c in enumerate(citations[:3], start=1):
                snippet = c.snippet.strip()
                if snippet:
                    bullet_points.append(
                        f"According to **{c.document_name}** (Page {c.page_number or '—'}, *{c.section or 'General'}*) [{idx}]:\n{snippet}"
                    )
            
            if selected_lang in ["mr", "marathi"]:
                synthesized = (
                    f"महाविद्यालयाच्या अधिकृत दस्तऐवजांनुसार माहिती खालीलप्रमाणे आहे:\n\n"
                    + "\n\n".join(bullet_points)
                    + f"\n\n*अधिकृत माहिती MITAOE ज्ञान भांडारातून संकलित केली आहे.*"
                )
            elif selected_lang in ["hi", "hindi"]:
                synthesized = (
                    f"कॉलेज के आधिकारिक दस्तावेजों के अनुसार जानकारी निम्नलिखित है:\n\n"
                    + "\n\n".join(bullet_points)
                    + f"\n\n*यह आधिकारिक जानकारी MITAOE नॉलेज रिपॉजिटरी से ली गई है।* "
                )
            else:
                synthesized = (
                    f"Here is the official college information regarding your inquiry:\n\n"
                    + "\n\n".join(bullet_points)
                    + f"\n\n*Source documents are officially registered in the MITAOE knowledge repository. Please contact the respective department office if you require further procedural details.*"
                )

            topics_out, entities_out, sentiment_out = enrich_nlp_metadata(synthesized)

            return ChatResponse(
                answer=synthesized,
                sources=citations,
                retrieval_mode=retrieval_mode,
                language=selected_lang,
                topics=topics_out,
                entities=entities_out,
                sentiment=sentiment_out,
            )
        logger.error("Gemini authentication failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer generation provider is not properly configured.",
        )
    except (GenerationRateLimitError, GenerationServiceUnavailableError) as exc:
        logger.warning("Gemini capacity error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The answer generation service is currently experiencing high load. Please try again in a few moments.",
        )
    except GenerationTimeoutError as exc:
        logger.warning("Gemini timeout: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Answer generation timed out. Please try asking again.",
        )
    except GenerationError as exc:
        logger.error("Gemini generation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate grounded answer from context.",
        )


@router.get(
    "/knowledge-base",
    summary="List available official college knowledge documents",
)
async def get_knowledge_base_catalog():
    """Return catalog of official college knowledge documents and sample questions."""
    from app.retrieval.default_knowledge import OFFICIAL_COLLEGE_DOCUMENTS
    return {"documents": OFFICIAL_COLLEGE_DOCUMENTS}


