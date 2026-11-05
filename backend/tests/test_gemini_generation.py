"""Unit tests for GeminiGenerationService: prompt assembly, grounding, retries, and error handling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.exceptions import (
    GenerationAuthenticationError,
    GenerationError,
    GenerationRateLimitError,
    GenerationTimeoutError,
)
from app.generation.gemini import GeminiGenerationService


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "According to the academic policy [1], students must maintain 75% attendance to take exams."
    client.aio.models.generate_content = AsyncMock(return_value=mock_resp)
    return client


@pytest.mark.asyncio
async def test_gemini_generate_grounded_answer_success(mock_genai_client):
    """Verify that valid query and context trigger grounded generation with citation markers."""
    service = GeminiGenerationService(client=mock_genai_client)

    context = "[1] Document: Policy.pdf (Page 4)\nStudents must maintain 75% attendance."
    answer = await service.generate_answer(
        query="What is the attendance criteria?",
        context_text=context,
        history=[{"role": "user", "content": "Hi"}],
    )

    assert "[1]" in answer
    assert "75% attendance" in answer
    mock_genai_client.aio.models.generate_content.assert_called_once()
    _, kwargs = mock_genai_client.aio.models.generate_content.call_args
    assert "Strict Grounding Rules" in kwargs["config"].system_instruction
    assert "What is the attendance criteria?" in kwargs["contents"]


@pytest.mark.asyncio
async def test_gemini_empty_context_returns_grounded_fallback(mock_genai_client):
    """Verify that if context is empty, an honest fallback message is returned without calling the API."""
    service = GeminiGenerationService(client=mock_genai_client)

    answer = await service.generate_answer(
        query="What are the dates for convocation?",
        context_text="",
    )

    assert "I could not find information" in answer
    mock_genai_client.aio.models.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_gemini_missing_api_key_raises_auth_error():
    """Verify that instantiating and calling generate without an API key raises GenerationAuthenticationError."""
    service = GeminiGenerationService(client=None)

    with pytest.raises(GenerationAuthenticationError) as exc_info:
        await service.generate_answer("test query", "some context")

    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_rate_limit_retry_and_exhaustion(mock_genai_client):
    """Verify that HTTP 429 / resource_exhausted errors trigger bounded retries with backoff."""
    mock_genai_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("429 Resource Exhausted: Quota exceeded")
    )
    service = GeminiGenerationService(client=mock_genai_client)

    with pytest.raises(GenerationRateLimitError) as exc_info:
        await service.generate_answer("query", "context")

    assert "rate limit / quota exceeded" in str(exc_info.value)
    assert mock_genai_client.aio.models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_gemini_timeout_retry_and_exhaustion(mock_genai_client):
    """Verify that timeout errors trigger bounded retries before raising GenerationTimeoutError."""
    mock_genai_client.aio.models.generate_content = AsyncMock(
        side_effect=asyncio.TimeoutError()
    )
    service = GeminiGenerationService(client=mock_genai_client)

    with pytest.raises(GenerationTimeoutError) as exc_info:
        await service.generate_answer("query", "context")

    assert "timed out after retries" in str(exc_info.value)
    assert mock_genai_client.aio.models.generate_content.call_count == 3

