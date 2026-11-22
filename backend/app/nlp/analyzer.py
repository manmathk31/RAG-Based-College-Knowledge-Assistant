"""Natural Language Processing (NLP) modules for College Knowledge Assistant.

Satisfies Course Outcome 2 (CO2) of NLP Lab (2311217L):
1. Sentiment analysis of college feedback and student reviews (positive, negative, neutral).
2. Information extraction and Named Entity Recognition (NER) for college entities:
   - Course names
   - Fees and monetary values
   - Eligibility requirements
   - Admission dates and timelines
   - Placement statistics and recruiters
   - Academic regulations and policies
"""

import re
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SentimentAspect(BaseModel):
    aspect: str
    sentiment: str
    polarity: float
    snippet: str


class SentimentAnalysisResponse(BaseModel):
    text: str
    overall_sentiment: str = Field(description="positive, negative, or neutral")
    confidence: float
    polarity_score: float = Field(description="Normalized polarity from -1.0 to +1.0")
    aspects: List[SentimentAspect] = Field(default_factory=list)
    key_phrases: List[str] = Field(default_factory=list)
    summary: str


class ExtractedEntity(BaseModel):
    text: str
    category: str = Field(description="COURSE, FEE, ELIGIBILITY, DATE_DEADLINE, PLACEMENT, REGULATION, FACILITY")
    start: int
    end: int
    confidence: float
    context: Optional[str] = None


class EntityExtractionResponse(BaseModel):
    text: str
    total_entities: int
    entity_counts: Dict[str, int]
    entities: List[ExtractedEntity]
    structured_summary: Dict[str, List[str]]


class CollegeNLPService:
    """Pretrained and rule-augmented NLP processor for sentiment analysis and college entity extraction."""

    # Domain lexicons for Sentiment Analysis
    POSITIVE_WORDS = {
        "good", "great", "excellent", "supportive", "helpful", "best", "clean", "hygienic",
        "top", "friendly", "advanced", "modern", "well-equipped", "spacious", "high", "impressive",
        "cooperative", "qualified", "satisfactory", "peaceful", "encouraging", "outstanding",
        "punctual", "efficient", "transparent", "active", "decent", "fast", "superb", "secure"
    }

    NEGATIVE_WORDS = {
        "bad", "poor", "strict", "harsh", "slow", "dirty", "unhygienic", "rude", "delayed",
        "difficult", "expensive", "unfair", "crowded", "noisy", "unhelpful", "rigid", "frustrating",
        "complicated", "problem", "issue", "worst", "irregular", "confusing", "fail", "penalty",
        "punishment", "lacking", "broken", "unresponsive", "insufficient"
    }

    INTENSIFIERS = {"very", "extremely", "really", "highly", "super", "absolutely", "too"}
    NEGATORS = {"not", "never", "no", "hardly", "barely", "scarcely", "without", "isn't", "aren't", "wasn't", "didn't"}

    # Aspect keywords
    ASPECT_MAP = {
        "Academics & Faculty": ["faculty", "professor", "teacher", "teaching", "syllabus", "lecturer", "class", "lab", "academic", "coursework"],
        "Hostel & Living": ["hostel", "room", "warden", "bathroom", "washroom", "bed", "living", "accommodation", "curfew", "stay"],
        "Mess & Food": ["mess", "food", "canteen", "lunch", "dinner", "breakfast", "meal", "dining", "hygiene", "taste"],
        "Placements & Career": ["placement", "company", "companies", "package", "salary", "recruiter", "internship", "job", "drive", "tpo"],
        "Examinations & Grading": ["exam", "grading", "marks", "revaluation", "atkt", "backlog", "ese", "ise", "evaluation", "paper"],
        "Fees & Administration": ["fee", "fees", "accounts", "admin", "section", "refund", "receipt", "clerk", "scholarship", "mahadbt"],
        "Campus & Infrastructure": ["campus", "library", "wifi", "internet", "gym", "ground", "sports", "security", "gate", "parking"]
    }

    # Entity Patterns for Information Extraction (NER)
    PATTERNS: Dict[str, List[re.Pattern]] = {
        "COURSE": [
            re.compile(r"\b(B\.?Tech|M\.?Tech|Ph\.?D|Bachelor of Technology|Master of Technology)\b(?:\s+(?:in\s+)?([A-Za-z\s&/]+?)(?=\s+(?:programme|program|degree|course|department|admission|fees|eligibility|,|\.|$)))?", re.IGNORECASE),
            re.compile(r"\b(Computer Engineering|Information Technology|Mechanical Engineering|Civil Engineering|Electronics & Telecommunication|Chemical Engineering|AI & DS|Artificial Intelligence|Data Science|Robotics)\b", re.IGNORECASE),
        ],
        "FEE": [
            re.compile(r"\b(?:Rs\.?|INR|₹)\s*[\d,]+(?:\s*(?:per\s+(?:year|annum|semester|course)|/-)?)?\b", re.IGNORECASE),
            re.compile(r"\b(?:Tuition|Development|Hostel|Mess|Examination|Revaluation|Photocopy)\s+Fee(?:s)?\s*(?:is|of|:)?\s*(?:Rs\.?|INR|₹)?\s*[\d,]+\b", re.IGNORECASE),
            re.compile(r"\b\d+\s*Lakhs?\b", re.IGNORECASE),
        ],
        "ELIGIBILITY": [
            re.compile(r"\b(?:\d{2}%\s*(?:marks|aggregate)?|10\+2|HSC|Diploma|non-zero\s+(?:positive\s+)?score)\b", re.IGNORECASE),
            re.compile(r"\b(?:MHT-CET|JEE\s+Main|GATE)\s*(?:\d{4})?\b", re.IGNORECASE),
            re.compile(r"\b(?:CGPA\s*(?:of|>=|>=|above|minimum)?\s*\d(?:\.\d{1,2})?)\b", re.IGNORECASE),
            re.compile(r"\b(?:zero|no|without)\s+active\s+backlog(?:s)?\b", re.IGNORECASE),
        ],
        "DATE_DEADLINE": [
            re.compile(r"\bwithin\s+\d+\s+(?:working\s+)?days?\b", re.IGNORECASE),
            re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b(?:\s+\d{4})?", re.IGNORECASE),
            re.compile(r"\b(?:Semester|Sem)\s+[1-8]\b", re.IGNORECASE),
            re.compile(r"\bCAP\s+Round(?:\s+[I|II|III|1|2|3])?\b", re.IGNORECASE),
        ],
        "PLACEMENT": [
            re.compile(r"\b\d+(?:\.\d+)?\s*LPA\b", re.IGNORECASE),
            re.compile(r"\b(?:IBM|TCS|Infosys|Cognizant|Veritas|Cisco|BMC Software|ZS Associates|Accenture|Wipro)\b", re.IGNORECASE),
            re.compile(r"\b(?:Dream Company|Super Dream|Standard Offer|Placement Drive)\b", re.IGNORECASE),
            re.compile(r"\b\d+\+\s*companies\b", re.IGNORECASE),
        ],
        "REGULATION": [
            re.compile(r"\b(?:minimum\s+)?(?:75%|60%|40%|50%|100%)\s*(?:attendance|condonation|waiver|weightage)?\b", re.IGNORECASE),
            re.compile(r"\b(?:ISE|ESE|ATKT|Condonation|Book Bank Scheme|TFWS|EBC|MahaDBT)\b", re.IGNORECASE),
            re.compile(r"\b10-point\s+(?:absolute\s+)?grading\s+scale\b", re.IGNORECASE),
        ],
        "FACILITY": [
            re.compile(r"\b(?:Boys Hostel|Girls Hostel|Central Library|Digital Library|Health Center|Ambulance|Gymnasium|Sports Complex|Wi-Fi|Solar Water Heater)\b", re.IGNORECASE),
        ]
    }

    def analyze_sentiment(self, text: str) -> SentimentAnalysisResponse:
        """Analyze polarity and aspect sentiment of college student feedback."""
        if not text or not text.strip():
            return SentimentAnalysisResponse(
                text="",
                overall_sentiment="neutral",
                confidence=0.5,
                polarity_score=0.0,
                aspects=[],
                key_phrases=[],
                summary="Empty review text."
            )

        cleaned = text.strip()
        sentences = re.split(r"[.!?;\n]+", cleaned)
        sentences = [s.strip() for s in sentences if s.strip()]

        total_score = 0.0
        words_scored = 0
        detected_aspects: List[SentimentAspect] = []
        key_phrases: List[str] = []

        # Sentence-level analysis
        for sent in sentences:
            tokens = re.findall(r"\b[A-Za-z'-]+\b", sent.lower())
            sent_score = 0.0
            negated = False
            intensified = False

            for i, token in enumerate(tokens):
                if token in self.NEGATORS:
                    negated = True
                    continue
                if token in self.INTENSIFIERS:
                    intensified = True
                    continue

                weight = 1.0
                if intensified:
                    weight = 1.5
                    intensified = False

                if token in self.POSITIVE_WORDS:
                    val = -1.0 if negated else 1.0
                    sent_score += val * weight
                    words_scored += 1
                    key_phrases.append(f"{'not ' if negated else ''}{token}")
                    negated = False
                elif token in self.NEGATIVE_WORDS:
                    val = 0.7 if negated else -1.0
                    sent_score += val * weight
                    words_scored += 1
                    key_phrases.append(f"{'not ' if negated else ''}{token}")
                    negated = False
                else:
                    # Reset negator after 3 tokens
                    negated = False

            total_score += sent_score

            # Check aspect mention in this sentence
            for aspect_name, keywords in self.ASPECT_MAP.items():
                if any(kw in tokens for kw in keywords):
                    aspect_polarity = sent_score
                    if aspect_polarity > 0.3:
                        aspect_sent = "positive"
                    elif aspect_polarity < -0.3:
                        aspect_sent = "negative"
                    else:
                        aspect_sent = "neutral"

                    # Avoid duplicate aspects
                    if not any(a.aspect == aspect_name for a in detected_aspects):
                        detected_aspects.append(
                            SentimentAspect(
                                aspect=aspect_name,
                                sentiment=aspect_sent,
                                polarity=round(aspect_polarity, 2),
                                snippet=sent[:120]
                            )
                        )

        # Normalize score
        normalized_polarity = total_score / max(words_scored, 1)
        normalized_polarity = max(min(normalized_polarity, 1.0), -1.0)

        if normalized_polarity > 0.15:
            overall = "positive"
            confidence = min(0.65 + abs(normalized_polarity) * 0.35, 0.98)
        elif normalized_polarity < -0.15:
            overall = "negative"
            confidence = min(0.65 + abs(normalized_polarity) * 0.35, 0.98)
        else:
            overall = "neutral"
            confidence = 0.72

        # Generate summary
        pos_aspects = [a.aspect for a in detected_aspects if a.sentiment == "positive"]
        neg_aspects = [a.aspect for a in detected_aspects if a.sentiment == "negative"]

        if pos_aspects and neg_aspects:
            summary = f"Mixed sentiment: Positive feedback on {', '.join(pos_aspects[:2])}, with concerns noted regarding {', '.join(neg_aspects[:2])}."
        elif pos_aspects:
            summary = f"Positive feedback praising {', '.join(pos_aspects[:3])}."
        elif neg_aspects:
            summary = f"Constructive negative feedback highlighting issues with {', '.join(neg_aspects[:3])}."
        else:
            summary = f"General {overall} institutional feedback."

        return SentimentAnalysisResponse(
            text=cleaned,
            overall_sentiment=overall,
            confidence=round(confidence, 2),
            polarity_score=round(normalized_polarity, 2),
            aspects=detected_aspects,
            key_phrases=list(set(key_phrases))[:8],
            summary=summary
        )

    def extract_entities(self, text: str) -> EntityExtractionResponse:
        """Extract structured college entities (Course, Fee, Eligibility, Dates, Placement, Regulation, Facility)."""
        if not text or not text.strip():
            return EntityExtractionResponse(
                text="",
                total_entities=0,
                entity_counts={},
                entities=[],
                structured_summary={}
            )

        cleaned = text.strip()
        entities: List[ExtractedEntity] = []
        structured_summary: Dict[str, List[str]] = {
            "COURSE": [],
            "FEE": [],
            "ELIGIBILITY": [],
            "DATE_DEADLINE": [],
            "PLACEMENT": [],
            "REGULATION": [],
            "FACILITY": []
        }

        seen_spans = set()

        for category, patterns in self.PATTERNS.items():
            for pat in patterns:
                for match in pat.finditer(cleaned):
                    match_str = match.group(0).strip()
                    start, end = match.start(), match.end()

                    # Avoid overlapping duplicates
                    span_key = (start, end)
                    if any(abs(start - s) < 3 and abs(end - e) < 3 for s, e in seen_spans):
                        continue
                    seen_spans.add(span_key)

                    # Context snippet around entity
                    c_start = max(0, start - 25)
                    c_end = min(len(cleaned), end + 25)
                    context_snippet = cleaned[c_start:c_end]

                    entity = ExtractedEntity(
                        text=match_str,
                        category=category,
                        start=start,
                        end=end,
                        confidence=0.92,
                        context=context_snippet
                    )
                    entities.append(entity)

                    if match_str not in structured_summary[category]:
                        structured_summary[category].append(match_str)

        entities.sort(key=lambda e: e.start)

        entity_counts = {cat: len(items) for cat, items in structured_summary.items() if items}

        return EntityExtractionResponse(
            text=cleaned,
            total_entities=len(entities),
            entity_counts=entity_counts,
            entities=entities,
            structured_summary={k: v for k, v in structured_summary.items() if v}
        )


nlp_service = CollegeNLPService()
