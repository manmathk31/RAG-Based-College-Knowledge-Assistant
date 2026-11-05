"""Google Gemini API implementation of BaseGenerationService using the official google-genai SDK."""

import asyncio
import logging
from typing import Dict, List, Optional

from google import genai
from google.genai import types

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    GenerationAuthenticationError,
    GenerationError,
    GenerationRateLimitError,
    GenerationServiceUnavailableError,
    GenerationTimeoutError,
)
from app.generation.base import BaseGenerationService

logger = logging.getLogger(__name__)

GROUNDED_SYSTEM_INSTRUCTION = """You are the authoritative College Knowledge Assistant for students and staff.
Your task is to answer the student's question accurately using ONLY the provided official college document excerpts.

Strict Grounding Rules:
1. Base your answer strictly on the provided document excerpts.
2. Every factual statement must cite its source excerpt using bracketed numeric markers like [1], [2] corresponding to the excerpt numbers provided.
3. If the provided excerpts do not contain sufficient information to answer the question, clearly state: "I could not find information regarding this in the official college documents."
4. Never speculate, assume, or extrapolate facts, dates, course codes, deadlines, or fees that are not explicitly stated in the context.
5. Distinguish explicitly stated facts from helpful general explanations.
6. Keep responses clear, concise, well-structured, and helpful for college students."""


class GeminiGenerationService(BaseGenerationService):
    """Generates grounded answers using Google Gemini Flash models via google-genai SDK."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[genai.Client] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._model = self._settings.GEMINI_GENERATION_MODEL
        self._temperature = self._settings.GEMINI_TEMPERATURE
        self._max_output_tokens = self._settings.GEMINI_MAX_OUTPUT_TOKENS
        self._timeout = self._settings.GEMINI_TIMEOUT

        if client:
            self._client = client
        else:
            api_key = self._settings.GEMINI_API_KEY.strip() if self._settings.GEMINI_API_KEY else None
            if api_key:
                self._client = genai.Client(api_key=api_key)
            else:
                self._client = None
                logger.info("GeminiGenerationService initialized without GEMINI_API_KEY (mock/testing mode).")

    async def generate_answer(
        self,
        query: str,
        context_text: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate grounded answer using Gemini API with bounded exponential retries."""
        if not self._client:
            raise GenerationAuthenticationError(
                "GEMINI_API_KEY is not configured. Please provide a valid Google AI Studio API key."
            )

        if not query or not query.strip():
            raise GenerationError("Question string must not be empty.")

        # If no context was retrieved, return standard honest grounded fallback
        if not context_text or not context_text.strip():
            return "I could not find information regarding your question in the official college documents."

        # Construct prompt contents
        prompt_parts: List[str] = []

        if history:
            prompt_parts.append("Recent Conversation History:")
            for turn in history[-5:]:  # Include at most 5 recent turns for conversation continuity
                role = "Student" if turn.get("role") == "user" else "Assistant"
                prompt_parts.append(f"{role}: {turn.get('content', '')}")
            prompt_parts.append("\n")

        prompt_parts.append("Official College Document Excerpts:")
        prompt_parts.append("---")
        prompt_parts.append(context_text.strip())
        prompt_parts.append("---")
        prompt_parts.append(f"Student Question: {query.strip()}")
        prompt_parts.append("Please provide a helpful, grounded answer citing sources with [1], [2] where appropriate:")

        full_prompt = "\n\n".join(prompt_parts)

        config = types.GenerateContentConfig(
            system_instruction=GROUNDED_SYSTEM_INSTRUCTION,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
        )

        # Retry loop for transient rate limits or 503s
        max_retries = 3
        backoff = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug("Calling Gemini API (model=%s, attempt=%d)...", self._model, attempt)
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model,
                        contents=full_prompt,
                        config=config,
                    ),
                    timeout=self._timeout,
                )

                if not response or not response.text:
                    raise GenerationError("Gemini API returned an empty response.")

                return response.text.strip()

            except asyncio.TimeoutError as exc:
                logger.warning("Gemini API call timed out on attempt %d: %s", attempt, exc)
                if attempt == max_retries:
                    raise GenerationTimeoutError("Gemini answer generation timed out after retries.") from exc
                await asyncio.sleep(backoff)
                backoff *= 2.0

            except Exception as exc:
                exc_str = str(exc).lower()

                # Check for authentication failures (do not retry)
                if "api_key" in exc_str or "unauthenticated" in exc_str or "permission_denied" in exc_str:
                    logger.error("Gemini API authentication failed: %s", exc)
                    raise GenerationAuthenticationError(f"Gemini API authentication failed: {exc}") from exc

                # Check for rate limit / quota
                if "resource_exhausted" in exc_str or "429" in exc_str:
                    logger.warning("Gemini rate limit exceeded on attempt %d: %s", attempt, exc)
                    if attempt == max_retries:
                        raise GenerationRateLimitError("Gemini rate limit / quota exceeded after retries.") from exc
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue

                # Check for service unavailable
                if "unavailable" in exc_str or "503" in exc_str:
                    logger.warning("Gemini service unavailable on attempt %d: %s", attempt, exc)
                    if attempt == max_retries:
                        raise GenerationServiceUnavailableError("Gemini service is temporarily unavailable.") from exc
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue

                logger.error("Unhandled Gemini generation error: %s", exc)
                raise GenerationError(f"Failed to generate answer from Gemini: {exc}") from exc

        raise GenerationError("Answer generation failed after retries.")

