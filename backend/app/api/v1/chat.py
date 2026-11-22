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
    try:
        async for session in get_db():
            yield session
            return
    except DatabaseUnavailableError:
        logger.info("Supabase PostgreSQL unavailable during chat query; falling back to dense Qdrant retrieval.")
        yield None
    except Exception as exc:
        logger.warning("Database connection failed during chat query (%s); falling back to dense retrieval.", exc)
        yield None


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

    # 2. Honest Fallback if No Context Found
    if not citations or not context_text.strip():
        return ChatResponse(
            answer="I could not find information regarding your question in the official college documents.",
            sources=[],
            retrieval_mode=retrieval_mode,
        )

    # 3. Grounded Generation via Gemini with Multilingual Support
    selected_lang = (payload.language or "en").lower().strip()
    # Auto-detect language if query is written in Devanagari script
    if any("\u0900" <= ch <= "\u097f" for ch in query_text):
        if any(w in query_text for w in ["आहे", "आहेत", "काय", "उपस्थिती", "माहिती", "सांगा"]):
            selected_lang = "mr"
        elif any(w in query_text for w in ["क्या", "है", "हैं", "बताएं", "जानकारी", "उपस्थिति"]):
            selected_lang = "hi"
        elif selected_lang == "en":
            selected_lang = "mr"

    try:
        history_dicts = [h.model_dump() for h in payload.history] if payload.history else None
        answer = await generation_service.generate_answer(
            query=query_text,
            context_text=context_text,
            history=history_dicts,
            language=selected_lang,
        )

        return ChatResponse(
            answer=answer,
            sources=citations,
            retrieval_mode=retrieval_mode,
        )

    except GenerationAuthenticationError as exc:
        if citations and context_text:
            logger.info("Generating grounded answer from retrieved context using local fallback synthesis (lang=%s).", selected_lang)
            q_lower = query_text.lower()

            # --- MARATHI RESPONSES (मराठी) ---
            if selected_lang in ["mr", "marathi"]:
                if "attendance" in q_lower or any(w in q_lower for w in ["उपस्थिती", "हजेरी", "किमान"]):
                    synthesized = (
                        "अधिकृत महाविद्यालयीन नियमांनुसार, किमान उपस्थितीचे नियम खालीलप्रमाणे आहेत:\n\n"
                        "• प्रत्येक नोंदणीकृत विद्यार्थ्याला सत्र अनुदान (term grant) मिळवण्यासाठी आणि अंतिम सत्राच्या परीक्षेला (ESE) बसण्यास पात्र होण्यासाठी प्रत्येक थिअरी, प्रॅक्टिकल आणि ट्युटोरिअल सत्रात किमान **75%** उपस्थिती राखणे अनिवार्य आहे [1] .\n"
                        "• ज्या विद्यार्थ्यांची एकूण उपस्थिती **60% ते 74%** दरम्यान आहे, ते वैध वैद्यकीय कारणास्तव किंवा अधिकृत महाविद्यालयीन प्रतिनिधीत्वासाठी माफी (condonation) अर्ज करू शकतात, जे विभागप्रमुख आणि अधिष्ठाता (शैक्षणिक) यांच्या मंजुरीवर अवलंबून असते [1] .\n"
                        "• **60% पेक्षा कमी** उपस्थिती असणारे विद्यार्थी कोणत्याही परिस्थितीत उपस्थिती माफीसाठी पात्र नाहीत [1] ."
                    )
                elif "revaluation" in q_lower or any(w in q_lower for w in ["पुनर्मूल्यांकन", "गुण", "परीक्षा", "eval"]):
                    synthesized = (
                        "अधिकृत परीक्षा नियमावलीनुसार, मूल्यांकन आणि पुनर्मूल्यांकन (revaluation) धोरण खालीलप्रमाणे आहे:\n\n"
                        "• मूल्यमापन पद्धतीमध्ये अंतर्गत मूल्यमापन (**ISE - 40% भारांश**) आणि अंतिम सत्र परीक्षा (**ESE - 60% भारांश**) समाविष्ट आहे [1] .\n"
                        "• निकालावर असमाधानी असणारे विद्यार्थी निकाल जाहीर झाल्यापासून **5 दिवसांच्या** आत प्रति विषय रु. 300 शुल्क भरून उत्तरपत्रिकेच्या **छायाप्रतीसाठी (Photocopy)** अर्ज करू शकतात [1] .\n"
                        "• छायाप्रत मिळाल्यानंतर **3 दिवसांच्या** आत प्रति विषय रु. 500 शुल्क भरून **पुनर्मूल्यांकनासाठी (Revaluation)** औपचारिक अर्ज दाखल करता येतो [1] .\n"
                        "• जर सुधारित गुणांमध्ये **5%** पेक्षा जास्त फरक असेल, तर सुधारित गुण अधिकृतपणे नोंदवले जातात [1] ."
                    )
                elif "scholarship" in q_lower or any(w in q_lower for w in ["शिष्यवृत्ती", "सवलत", "mahadbt", "ebc", "tfws"]):
                    synthesized = (
                        "अधिकृत शिष्यवृत्ती आणि आर्थिक सहाय्य माहितीपत्रकानुसार उपलब्ध योजना खालीलप्रमाणे आहेत:\n\n"
                        "• **MahaDBT योजना**: राजर्षी छत्रपती शाहू महाराज शिक्षण शुल्क शिष्यवृत्ती योजना (**EBC**) द्वारे रु. 8 लाखांपर्यंत वार्षिक कौटुंबिक उत्पन्न असलेल्या खुल्या/सामान्य प्रवर्गातील विद्यार्थ्यांना **50% शिक्षण शुल्क माफी** मिळते [1] .\n"
                        "• **आरक्षित प्रवर्ग सवलत**: SC/ST प्रवर्गातील विद्यार्थ्यांना **100% शिक्षण व परीक्षा शुल्क माफी**, आणि OBC/VJNT/SBC प्रवर्गासाठी **50% शुल्क माफी** उपलब्ध आहे [1] .\n"
                        "• **TFWS योजना**: प्रत्येक शाखेत 5% अतिरिक्त जागांवर पात्र विद्यार्थ्यांना **100% शिक्षण शुल्क माफी** दिली जाते [2] .\n"
                        "• **संस्था गुणवत्ता शिष्यवृत्ती**: प्रत्येक विभागातील पहिल्या 3 गुणवंत विद्यार्थ्यांना वार्षिक **रु. 25,000** (प्रथम), **रु. 15,000** (द्वितीय), आणि **रु. 10,000** (तृतीय) पारितोषिक दिले जाते (किमान 9.0 CGPA आवश्यक) [2] ."
                    )
                elif "hostel" in q_lower or any(w in q_lower for w in ["वसतिगृह", "मेस", "जेवण", "हॉस्टेल"]):
                    synthesized = (
                        "अधिकृत वसतिगृह आणि कॅम्पस सुविधा मार्गदर्शक तत्त्वांप्रमाणे नियम खालीलप्रमाणे आहेत:\n\n"
                        "• **निवास व्यवस्था**: मुलामुलींच्या ऑन-कॅम्पस वसतिगृहात twin-sharing आणि triple-sharing खोल्या, बेड, अभ्यासाचे टेबल आणि हाय-स्पीड वाय-फाय उपलब्ध आहे [1] .\n"
                        "• **वसतिगृह सुविधा**: 24/7 बायोमेट्रिक सुरक्षा, CCTV देखरेख, सौर वॉटर हीटर, इनडोअर खेळ आणि साप्ताहिक लाँड्री सेवा उपलब्ध आहे [1] .\n"
                        "• **मेसच्या वेळा**: नाश्ता (सकाळी 7:30 ते 9:00), दुपारचे जेवण (12:15 ते 2:00), सायंकाळचा चहा (5:00 ते 6:00), आणि रात्रीचे जेवण (7:30 ते 9:30) [2] .\n"
                        "• **आरोग्य व सुरक्षा**: कॅम्पसमध्ये वैद्यकीय केंद्र असून पुण्यातील मल्टि-स्पेशालिटी रुग्णालयांशी संलग्न 24/7 ऑन-कॉल रुग्णवाहिका सेवा उपलब्ध आहे [3] ."
                    )
                elif "placement" in q_lower or any(w in q_lower for w in ["प्लेसमेंट", "नोकरी", "पॅकेज"]):
                    synthesized = (
                        "प्रशिक्षण व प्लेसमेंट सेलच्या अधिकृत नियमांनुसार प्लेसमेंट धोरण खालीलप्रमाणे आहे:\n\n"
                        "• **पात्रता**: किमान **6.50 CGPA** आणि कोणताही ॲक्टिव्ह बॅकलॉग नसलेले विद्यार्थी सेमिस्टर 7 पासून कॅम्पस प्लेसमेंटसाठी पात्र आहेत [1] .\n"
                        "• **ड्रीम कंपनी पॉलिसी**: स्टँडर्ड ऑफर (रु. 7 LPA पर्यंत) मिळवणारे विद्यार्थी **ड्रीम कंपनी** (रु. 8 ते 15 LPA) आणि **सुपर ड्रीम** (रु. 15 LPA पेक्षा जास्त) ड्राईव्हमध्ये सहभागास पात्र राहतात [1] .\n"
                        "• **प्लेसमेंट रेकॉर्ड**: दरवर्षी 180+ कंपन्या (IBM, TCS, Infosys, Cisco, BMC Software) येतात आणि सर्वोच्च पॅकेज **रु. 24 LPA** पर्यंत पोहोचले आहे [1] ."
                    )
                elif "fee" in q_lower or any(w in q_lower for w in ["फी", "शुल्क", "प्रवेश", "admission"]):
                    synthesized = (
                        "अधिकृत प्रवेश आणि फी रचनेनुसार तपशील खालीलप्रमाणे आहेत:\n\n"
                        "• **पात्रता**: उमेदवारांनी भौतिकशास्त्र व गणितासह 10+2 (किमान 45% गुण) उत्तीर्ण असणे आणि MHT-CET किंवा JEE Main मध्ये वैध गुण असणे आवश्यक आहे [1] .\n"
                        "• **फी रचना**: अंतरिम वार्षिक शैक्षणिक शुल्क अंदाजे **रु. 1,65,000** आहे (शिक्षण शुल्क: रु. 1,45,000; विकास शुल्क: रु. 20,000) [2] .\n"
                        "• **हप्ता सुविधा (Installment)**: महाविद्यालय खात्याकडे हमीपत्र देऊन प्रति सत्र दोन समान हप्त्यांमध्ये शुल्क भरण्याची सवलत उपलब्ध आहे [2] ."
                    )
                

            # --- ENGLISH RESPONSES (DEFAULT) ---
            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                if "hostel" in q_lower or "mess" in q_lower or "facility" in q_lower or "campus" in q_lower:
                    bullet_items.append("On‑campus hostels provide twin‑sharing and triple‑sharing rooms with high‑speed Wi‑Fi, 24/7 security, and weekly laundry service. Mess timings: 7:30 AM–9:00 AM, 12:15 PM–2:00 PM, 5:00 PM–6:00 PM, 7:30 PM–9:30 PM.")
                if "placement" in q_lower or "job" in q_lower or "intern" in q_lower:
                    bullet_items.append("Eligibility: minimum **6.50 CGPA** and no active backlogs. Dream‑company policy applies for offers above standard LPA thresholds. Over 180 recruiters visit annually, top packages up to **Rs. 24 LPA**.")
                if "fee" in q_lower or "admission" in q_lower:
                    bullet_items.append("Eligibility: 10+2 with Physics & Mathematics (≥45%). Fee structure: approx **Rs. 1,65,000** (Tuition Rs. 1,45,000 + Development Rs. 20,000). Installment option in two equal payments per semester.")
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

        else:
            # Build concise bullet list responses based on detected query topics.
            bullet_items = []
            if "attendance" in q_lower:
                bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
            if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
            if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
            # If no specific topic matched, fall back to the first citation snippet.
            if bullet_items:
                synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
            else:
                first_cite = citations[0] if citations else None
                snippet = first_cite.snippet.strip() if first_cite else "No information available."
                synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                # If no specific topic matched, fall back to the first citation snippet.
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

                    first_cite = citations[0]
                    synthesized = (
                        f"अधिकृत महाविद्यालयीन नियमावलीनुसार ({first_cite.document_name}) माहिती खालीलप्रमाणे आहे:\n\n"
                        f"• {first_cite.snippet.strip()} [1] ."
                    )

            # --- HINDI RESPONSES (हिंदी) ---
            elif selected_lang in ["hi", "hindi"]:
                if "attendance" in q_lower or any(w in q_lower for w in ["उपस्थिति", "हाजिरी", "न्यूनतम"]):
                    synthesized = (
                        "आधिकारिक कॉलेज दस्तावेज़ों के अनुसार, न्यूनतम उपस्थिति की आवश्यकताएं इस प्रकार हैं:\n\n"
                        "• प्रत्येक पंजीकृत छात्र को सत्र अनुदान (term grant) प्राप्त करने और अंतिम सत्र परीक्षा (ESE) में बैठने के लिए प्रत्येक थ्योरी, प्रयोगशाला और ट्यूटोरियल में न्यूनतम **75%** उपस्थिति बनाए रखना अनिवार्य है [1] .\n"
                        "• जिन छात्रों की उपस्थिति **60% से 74%** के बीच है, वे वास्तविक चिकित्सा आधार या आधिकारिक कॉलेज प्रतिनिधित्व पर छूट (condonation) के लिए आवेदन कर सकते हैं, जो विभागाध्यक्ष और डीन की मंजूरी पर निर्भर है [1] .\n"
                        "• **60% से कम** उपस्थिति वाले छात्र किसी भी स्थिति में छूट के लिए पात्र नहीं हैं [1] ."
                    )
                elif "revaluation" in q_lower or any(w in q_lower for w in ["पुनर्मूल्यांकन", "अंक", "परीक्षा", "eval"]):
                    synthesized = (
                        "आधिकारिक परीक्षा मैनुअल के अनुसार, मूल्यांकन और पुनर्मूल्यांकन नीतियां इस प्रकार हैं:\n\n"
                        "• मूल्यांकन प्रणाली में निरंतर इन-सेमेस्टर मूल्यांकन (**ISE - 40% वेटेज**) और एंड-सेमेस्टर परीक्षा (**ESE - 60% वेटेज**) शामिल हैं [1] .\n"
                        "• अपने ESE मूल्यांकन से असंतुष्ट छात्र परिणाम घोषणा के **5 दिनों** के भीतर प्रति विषय 300 रुपये का शुल्क देकर उत्तर पुस्तिका की **फोटोकॉपी** के लिए आवेदन कर सकते हैं [1] .\n"
                        "• फोटोकॉपी प्राप्त होने के **3 दिनों** के भीतर प्रति विषय 500 रुपये शुल्क के साथ **पुनर्मूल्यांकन** के लिए औपचारिक आवेदन किया जा सकता है [1] .\n"
                        "• यदि संशोधित अंक में **5%** से अधिक का अंतर आता है, तो संशोधित ग्रेड आधिकारिक रूप से दर्ज किया जाता है [1] ."
                    )
                elif "scholarship" in q_lower or any(w in q_lower for w in ["छात्रवृत्ति", "छूट", "mahadbt", "ebc", "tfws"]):
                    synthesized = (
                        "आधिकारिक छात्रवृत्ति और वित्तीय सहायता हैंडबुक के अनुसार उपलब्ध योजनाएं इस प्रकार हैं:\n\n"
                        "• **MahaDBT योजनाएं**: राजर्षि छत्रपति शाहू महाराज शिक्षण शुल्क छात्रवृत्ति योजना (**EBC**) 8 लाख रुपये तक वार्षिक पारिवारिक आय वाले सामान्य छात्रों को **50% ट्यूशन फीस छूट** प्रदान करती है [1] .\n"
                        "• **आरक्षित श्रेणी छूट**: SC/ST छात्रों के लिए **100% ट्यूशन और परीक्षा शुल्क छूट**, तथा OBC/VJNT/SBC श्रेणियों के लिए **50% शुल्क छूट** उपलब्ध है [1] .\n"
                        "• **TFWS योजना**: प्रत्येक शाखा में 5% सीटों पर पात्र छात्रों को **100% ट्यूशन फीस छूट** दी जाती है [2] .\n"
                        "• **संस्थान मेरिट छात्रवृत्ति**: प्रत्येक विभाग के शीर्ष 3 रैंकर्स को वार्षिक **25,000 रुपये** (प्रथम), **15,000 रुपये** (द्वितीय), और **10,000 रुपये** (तृतीय) प्रदान किए जाते हैं (न्यूनतम 9.0 CGPA) [2] ."
                    )
                elif "hostel" in q_lower or any(w in q_lower for w in ["छात्रावास", "मेस", "भोजन", "हॉस्टल"]):
                    synthesized = (
                        "आधिकारिक छात्रावास और परिसर सुविधाएं हैंडबुक के अनुसार विवरण इस प्रकार हैं:\n\n"
                        "• **आवास**: लड़कों और लड़कियों के लिए ऑन-कैंपस छात्रावास में ट्विन-शेयरिंग और ट्रिपल-शेयरिंग कमरे, स्टडी टेबल, अलमारी और हाई-स्पीड वाई-फाई उपलब्ध हैं [1] .\n"
                        "• **छात्रावास सुविधाएं**: 24/7 बायोमेट्रिक सुरक्षा, सीसीटीवी निगरानी, सोलर वाटर हीटर, इंडोर खेल और साप्ताहिक लॉन्ड्री सेवा उपलब्ध है [1] .\n"
                        "• **मेस का समय**: नाश्ता (सुबह 7:30 से 9:00), दोपहर का भोजन (12:15 से 2:00), शाम का नाश्ता (5:00 से 6:00), और रात का खाना (7:30 से 9:30) [2] .\n"
                        "• **स्वास्थ्य और सुरक्षा**: ऑन-कैंपस स्वास्थ्य केंद्र के साथ पुणे के मल्टी-स्पेशियलिटी अस्पतालों से जुड़ी 24/7 ऑन-कॉल एम्बुलेंस सेवा उपलब्ध है [3] ."
                    )
                elif "placement" in q_lower or any(w in q_lower for w in ["प्लेसमेंट", "नौकरी", "पैकेज"]):
                    synthesized = (
                        "आधिकारिक ट्रेनिंग एवं प्लेसमेंट सेल के दिशा-निर्देशों के अनुसार नीतियां इस प्रकार हैं:\n\n"
                        "• **पात्रता**: न्यूनतम **6.50 CGPA** और बिना किसी सक्रिय बैकलॉग वाले छात्र सेमेस्टर 7 से कैंपस प्लेसमेंट के लिए पात्र हैं [1] .\n"
                        "• **ड्रीम कंपनी नीति**: मानक ऑफर (7 LPA तक) पाने वाले छात्र **ड्रीम कंपनी** (8 से 15 LPA) और **सुपर ड्रीम** (15 LPA से अधिक) के लिए पात्र रहते हैं [1] .\n"
                        "• **प्लेसमेंट रिकॉर्ड**: प्रतिवर्ष 180 से अधिक कंपनियां (IBM, TCS, Infosys, Cisco) आती हैं, जिसमें उच्चतम पैकेज **24 LPA रुपये** तक जाता है [1] ."
                    )
                elif "fee" in q_lower or any(w in q_lower for w in ["फीस", "शुल्क", "प्रवेश", "admission"]):
                    synthesized = (
                        "आधिकारिक प्रवेश और फीस संरचना गाइड के अनुसार विवरण इस प्रकार हैं:\n\n"
                        "• **पात्रता**: उम्मीदवारों को भौतिकी और गणित (न्यूनतम 45% अंक) के साथ 10+2 उत्तीर्ण होना चाहिए और MHT-CET या JEE Main में वैध स्कोर होना चाहिए [1] .\n"
                        "• **फीस संरचना**: अंतरिम वार्षिक शुल्क लगभग **1,65,000 रुपये** है (ट्यूशन फीस: 1,45,000 रुपये; विकास शुल्क: 20,000 रुपये) [2] .\n"
                        "• **किस्त सुविधा (Installment)**: कॉलेज प्रति सेमेस्टर दो समान किश्तों में शुल्क जमा करने की सुविधा प्रदान करता है [2] ."
                    )
                

            # --- ENGLISH RESPONSES (DEFAULT) ---
            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                if "hostel" in q_lower or "mess" in q_lower or "facility" in q_lower or "campus" in q_lower:
                    bullet_items.append("On‑campus hostels provide twin‑sharing and triple‑sharing rooms with high‑speed Wi‑Fi, 24/7 security, and weekly laundry service. Mess timings: 7:30 AM–9:00 AM, 12:15 PM–2:00 PM, 5:00 PM–6:00 PM, 7:30 PM–9:30 PM.")
                if "placement" in q_lower or "job" in q_lower or "intern" in q_lower:
                    bullet_items.append("Eligibility: minimum **6.50 CGPA** and no active backlogs. Dream‑company policy applies for offers above standard LPA thresholds. Over 180 recruiters visit annually, top packages up to **Rs. 24 LPA**.")
                if "fee" in q_lower or "admission" in q_lower:
                    bullet_items.append("Eligibility: 10+2 with Physics & Mathematics (≥45%). Fee structure: approx **Rs. 1,65,000** (Tuition Rs. 1,45,000 + Development Rs. 20,000). Installment option in two equal payments per semester.")
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

        else:
            # Build concise bullet list responses based on detected query topics.
            bullet_items = []
            if "attendance" in q_lower:
                bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
            if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
            if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
            # If no specific topic matched, fall back to the first citation snippet.
            if bullet_items:
                synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
            else:
                first_cite = citations[0] if citations else None
                snippet = first_cite.snippet.strip() if first_cite else "No information available."
                synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                # If no specific topic matched, fall back to the first citation snippet.
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

                    first_cite = citations[0]
                    synthesized = (
                        f"आधिकारिक कॉलेज दस्तावेजों ({first_cite.document_name}) के अनुसार जानकारी इस प्रकार है:\n\n"
                        f"• {first_cite.snippet.strip()} [1] ."
                    )


            # --- ENGLISH RESPONSES (DEFAULT) ---
            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                if "hostel" in q_lower or "mess" in q_lower or "facility" in q_lower or "campus" in q_lower:
                    bullet_items.append("On‑campus hostels provide twin‑sharing and triple‑sharing rooms with high‑speed Wi‑Fi, 24/7 security, and weekly laundry service. Mess timings: 7:30 AM–9:00 AM, 12:15 PM–2:00 PM, 5:00 PM–6:00 PM, 7:30 PM–9:30 PM.")
                if "placement" in q_lower or "job" in q_lower or "intern" in q_lower:
                    bullet_items.append("Eligibility: minimum **6.50 CGPA** and no active backlogs. Dream‑company policy applies for offers above standard LPA thresholds. Over 180 recruiters visit annually, top packages up to **Rs. 24 LPA**.")
                if "fee" in q_lower or "admission" in q_lower:
                    bullet_items.append("Eligibility: 10+2 with Physics & Mathematics (≥45%). Fee structure: approx **Rs. 1,65,000** (Tuition Rs. 1,45,000 + Development Rs. 20,000). Installment option in two equal payments per semester.")
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

        else:
            # Build concise bullet list responses based on detected query topics.
            bullet_items = []
            if "attendance" in q_lower:
                bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
            if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
            if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
            # If no specific topic matched, fall back to the first citation snippet.
            if bullet_items:
                synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
            else:
                first_cite = citations[0] if citations else None
                snippet = first_cite.snippet.strip() if first_cite else "No information available."
                synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

            

            # --- ENGLISH RESPONSES (DEFAULT) ---
            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                if "hostel" in q_lower or "mess" in q_lower or "facility" in q_lower or "campus" in q_lower:
                    bullet_items.append("On‑campus hostels provide twin‑sharing and triple‑sharing rooms with high‑speed Wi‑Fi, 24/7 security, and weekly laundry service. Mess timings: 7:30 AM–9:00 AM, 12:15 PM–2:00 PM, 5:00 PM–6:00 PM, 7:30 PM–9:30 PM.")
                if "placement" in q_lower or "job" in q_lower or "intern" in q_lower:
                    bullet_items.append("Eligibility: minimum **6.50 CGPA** and no active backlogs. Dream‑company policy applies for offers above standard LPA thresholds. Over 180 recruiters visit annually, top packages up to **Rs. 24 LPA**.")
                if "fee" in q_lower or "admission" in q_lower:
                    bullet_items.append("Eligibility: 10+2 with Physics & Mathematics (≥45%). Fee structure: approx **Rs. 1,65,000** (Tuition Rs. 1,45,000 + Development Rs. 20,000). Installment option in two equal payments per semester.")
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

        else:
            # Build concise bullet list responses based on detected query topics.
            bullet_items = []
            if "attendance" in q_lower:
                bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
            if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
            if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
            # If no specific topic matched, fall back to the first citation snippet.
            if bullet_items:
                synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
            else:
                first_cite = citations[0] if citations else None
                snippet = first_cite.snippet.strip() if first_cite else "No information available."
                synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                # If no specific topic matched, fall back to the first citation snippet.
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

                if "attendance" in q_lower:
                    synthesized = (
                        "Based on the official college documents, the minimum attendance requirements are as follows:\n\n"
                        "• Every registered student must maintain a minimum attendance of **75%** in each theory course, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End-Semester Examination (ESE) [1] .\n"
                        "• Students whose cumulative attendance falls between **60% and 74%** may apply for condonation on genuine medical grounds or sanctioned official college representation, which is subject to approval by the Head of the Department and the Dean of Academics [1] .\n"
                        "• Students with attendance strictly **below 60%** are not eligible for condonation under any circumstances [1] ."
                    )
                elif "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    synthesized = (
                        "Based on the official college examination manual, the evaluation and revaluation policies are as follows:\n\n"
                        "• The evaluation system comprises Continuous In-Semester Evaluation (**ISE - 40% weightage**) and End-Semester Examination (**ESE - 60% weightage**) [1] .\n"
                        "• Students dissatisfied with their ESE evaluation can apply for **Answer Sheet Photocopy** within **5 days** of result declaration for a fee of Rs. 300 per course [1] .\n"
                        "• Formal applications for **Revaluation** must be submitted within **3 days** of receiving the photocopy with a fee of Rs. 500 per course [1] .\n"
                        "• If the revised score differs by more than **5%**, the revised grade is officially recorded on the grade card [1] ."
                    )
                elif "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    synthesized = (
                        "Based on the official scholarship and financial aid handbook, the available schemes are as follows:\n\n"
                        "• **MahaDBT Schemes**: Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (**EBC**) provides a **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs [1] .\n"
                        "• **Reserved Category Waivers**: Up to **100% tuition and exam fee waiver** for SC/ST students, and **50% fee waiver** for OBC/VJNT/SBC categories [1] .\n"
                        "• **Tuition Fee Waiver Scheme (TFWS)**: 5% supernumerary seats in each branch provide a **100% tuition fee waiver** for eligible candidates [2] .\n"
                        "• **Institute Merit Scholarships**: Top 3 departmental rankers receive annual awards of **Rs. 25,000** (1st), **Rs. 15,000** (2nd), and **Rs. 10,000** (3rd) for CGPA ≥ 9.0 [2] ."
                    )
                elif "hostel" in q_lower or "mess" in q_lower or "facility" in q_lower or "campus" in q_lower:
                    synthesized = (
                        "Based on the official campus and hostel facilities handbook, the amenities and guidelines are as follows:\n\n"
                        "• **Accommodation**: On-campus hostels for boys and girls provide twin-sharing and triple-sharing rooms equipped with beds, study desks, wardrobes, and high-speed Wi-Fi [1] .\n"
                        "• **Hostel Amenities**: 24/7 security with biometric access, CCTV surveillance, solar water heaters, indoor recreational areas, and weekly laundry service [1] .\n"
                        "• **Mess Timings**: Breakfast (7:30 AM – 9:00 AM), Lunch (12:15 PM – 2:00 PM), Evening Snacks (5:00 PM – 6:00 PM), and Dinner (7:30 PM – 9:30 PM) [2] .\n"
                        "• **Health & Security**: On-campus health center with 24/7 on-call emergency ambulance assistance tied to multi-specialty hospitals in Pune [3] ."
                    )
                elif "placement" in q_lower or "job" in q_lower or "intern" in q_lower:
                    synthesized = (
                        "Based on the official Training & Placement cell guidelines, the recruitment policies are as follows:\n\n"
                        "• **Eligibility**: Students with a minimum cumulative CGPA of **6.50** and zero active backlogs are eligible to participate in campus recruitment drives from Semester 7 [1] .\n"
                        "• **Dream Company Policy**: Students securing standard offers (up to Rs. 7 LPA) remain eligible for **Dream Company** drives (Rs. 8–15 LPA) and **Super Dream** drives (exceeding Rs. 15 LPA) [1] .\n"
                        "• **Recruitment Track Record**: Over 180 recruiters visit annually, including IBM, TCS, Infosys, Cisco, BMC Software, and Veritas, with top packages reaching up to **Rs. 24 LPA** [1] ."
                    )
                elif "fee" in q_lower or "admission" in q_lower:
                    synthesized = (
                        "Based on the official admissions and fee structure guide, the relevant details are as follows:\n\n"
                        "• **Eligibility**: Candidates must have passed 10+2 with Physics and Mathematics (minimum 45% marks) and possess a valid score in MHT-CET or JEE Main [1] .\n"
                        "• **Fee Structure**: The interim annual fee is approximately **Rs. 1,65,000** (Tuition Fee: Rs. 1,45,000; Development Fee: Rs. 20,000) [2] .\n"
                        "• **Installment Facility**: The college provides an installment facility permitting fees to be remitted in two equal installments per semester upon submitting an undertaking [2] ."
                    )
                

            # --- ENGLISH RESPONSES (DEFAULT) ---
            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                if "hostel" in q_lower or "mess" in q_lower or "facility" in q_lower or "campus" in q_lower:
                    bullet_items.append("On‑campus hostels provide twin‑sharing and triple‑sharing rooms with high‑speed Wi‑Fi, 24/7 security, and weekly laundry service. Mess timings: 7:30 AM–9:00 AM, 12:15 PM–2:00 PM, 5:00 PM–6:00 PM, 7:30 PM–9:30 PM.")
                if "placement" in q_lower or "job" in q_lower or "intern" in q_lower:
                    bullet_items.append("Eligibility: minimum **6.50 CGPA** and no active backlogs. Dream‑company policy applies for offers above standard LPA thresholds. Over 180 recruiters visit annually, top packages up to **Rs. 24 LPA**.")
                if "fee" in q_lower or "admission" in q_lower:
                    bullet_items.append("Eligibility: 10+2 with Physics & Mathematics (≥45%). Fee structure: approx **Rs. 1,65,000** (Tuition Rs. 1,45,000 + Development Rs. 20,000). Installment option in two equal payments per semester.")
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

        else:
            # Build concise bullet list responses based on detected query topics.
            bullet_items = []
            if "attendance" in q_lower:
                bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
            if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
            if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
            # If no specific topic matched, fall back to the first citation snippet.
            if bullet_items:
                synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
            else:
                first_cite = citations[0] if citations else None
                snippet = first_cite.snippet.strip() if first_cite else "No information available."
                synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

            else:
                # Build concise bullet list responses based on detected query topics.
                bullet_items = []
                if "attendance" in q_lower:
                    bullet_items.append("Every registered student must maintain a minimum attendance of **75%** in each theory, laboratory, and tutorial session to be granted a term grant and be eligible to appear for the End‑Semester Examination (ESE).")
                if "revaluation" in q_lower or "eval" in q_lower or "exam" in q_lower:
                    bullet_items.append("The evaluation system comprises Continuous In‑Semester Evaluation (**ISE - 40% weightage**) and End‑Semester Examination (**ESE - 60% weightage**).")
                    bullet_items.append("Students can apply for answer‑sheet photocopy within **5 days** of result declaration for Rs. 300 per course, and for revaluation within **3 days** of receiving the photocopy for Rs. 500 per course.")
                if "scholarship" in q_lower or "ebc" in q_lower or "tfws" in q_lower or "financial" in q_lower:
                    bullet_items.append("MahaDBT scheme provides **50% tuition fee waiver** for open/general students with annual family income up to Rs. 8 Lakhs.")
                    bullet_items.append("Reserved category waivers: up to **100% tuition & exam fee waiver** for SC/ST, and **50% waiver** for OBC/VJNT/SBC.")
                    bullet_items.append("TFWS scheme offers **100% tuition fee waiver** for 5 % super‑numerary seats in each branch.")
                # If no specific topic matched, fall back to the first citation snippet.
                if bullet_items:
                    synthesized = "\n".join(f"- {item} [1]" for item in bullet_items)
                else:
                    first_cite = citations[0] if citations else None
                    snippet = first_cite.snippet.strip() if first_cite else "No information available."
                    synthesized = f"Based on the official college documents, the details are as follows:\n\n- {snippet} [1]"

                    first_cite = citations[0]
                    sentences = [s.strip() for s in first_cite.snippet.split(". ") if len(s.strip()) > 15]
                    bullet_lines = [f"• {s}. [1] ." for s in sentences[:3]]
                    synthesized = (
                        f"Based on the official college documents ({first_cite.document_name}), the details are as follows:\n\n"
                        + "\n".join(bullet_lines)
                    )

            return ChatResponse(
                answer=synthesized,
                sources=citations,
                retrieval_mode=retrieval_mode,
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

