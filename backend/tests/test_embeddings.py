"""Targeted unit tests for Hugging Face hosted embedding service."""

from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import pytest
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

from app.core.config import Settings
from app.core.exceptions import (
    EmbeddingAuthenticationError,
    EmbeddingDimensionMismatchError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
)
from app.embeddings.huggingface import HuggingFaceEmbeddingService


@pytest.fixture
def custom_settings() -> Settings:
    return Settings(
        HF_TOKEN="fake-test-token",
        EMBEDDING_PROVIDER="huggingface",
        EMBEDDING_MODEL="BAAI/bge-small-en-v1.5",
        EMBEDDING_DIMENSION=384,
        EMBEDDING_BATCH_SIZE=2,
        EMBEDDING_TIMEOUT=5.0,
        EMBEDDING_MAX_RETRIES=2,
    )


@pytest.mark.asyncio
async def test_embed_single_text_success(custom_settings: Settings) -> None:
    """Verify single text embedding produces a 384-dimensional float vector."""
    mock_client = MagicMock()
    mock_vector = np.full((1, 384), 0.123, dtype=np.float32)
    mock_client.feature_extraction = AsyncMock(return_value=mock_vector)

    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)
    result = await service.embed_text("What are the admission requirements for Computer Science?")

    assert isinstance(result, list)
    assert len(result) == 384
    assert result[0] == pytest.approx(0.123, rel=1e-3)
    mock_client.feature_extraction.assert_called_once()


@pytest.mark.asyncio
async def test_embed_batch_success_and_chunking(custom_settings: Settings) -> None:
    """Verify batch embedding chunks requests to EMBEDDING_BATCH_SIZE (2) and aggregates results."""
    mock_client = MagicMock()

    # Batch size is 2, so 3 items will require 2 calls (batch 1: 2 items, batch 2: 1 item)
    vec1 = np.full((2, 384), 0.1, dtype=np.float32)
    vec2 = np.full((1, 384), 0.2, dtype=np.float32)
    mock_client.feature_extraction = AsyncMock(side_effect=[vec1, vec2])

    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)
    texts = [
        "First document text",
        "Second document text",
        "Third document text",
    ]
    results = await service.embed_batch(texts)

    assert len(results) == 3
    assert len(results[0]) == 384
    assert len(results[1]) == 384
    assert len(results[2]) == 384
    assert results[0][0] == pytest.approx(0.1, rel=1e-3)
    assert results[2][0] == pytest.approx(0.2, rel=1e-3)
    assert mock_client.feature_extraction.call_count == 2


@pytest.mark.asyncio
async def test_embed_empty_and_whitespace_input(custom_settings: Settings) -> None:
    """Verify invalid or empty inputs raise ValueError or return empty list."""
    mock_client = MagicMock()
    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)

    # Empty text
    with pytest.raises(ValueError, match="must not be empty"):
        await service.embed_text("")

    with pytest.raises(ValueError, match="must not be empty"):
        await service.embed_text("   ")

    # Empty batch returns empty list without calling API
    empty_res = await service.embed_batch([])
    assert empty_res == []
    mock_client.feature_extraction.assert_not_called()

    # Batch containing an invalid item
    with pytest.raises(ValueError, match="must be a non-empty string"):
        await service.embed_batch(["valid query", ""])


@pytest.mark.asyncio
async def test_dimension_mismatch_error(custom_settings: Settings) -> None:
    """Verify an error is raised when provider returns an incompatible dimension (e.g. 512 vs 384)."""
    mock_client = MagicMock()
    # Provider returns 512 dimensions instead of configured 384
    wrong_dim_vector = np.zeros((1, 512), dtype=np.float32)
    mock_client.feature_extraction = AsyncMock(return_value=wrong_dim_vector)

    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)
    with pytest.raises(EmbeddingDimensionMismatchError, match="Vector dimension mismatch"):
        await service.embed_text("Sample college syllabus snippet")


@pytest.mark.asyncio
async def test_rate_limit_retry_and_exhaustion(custom_settings: Settings) -> None:
    """Verify HTTP 429 rate limit is retried with backoff and raises EmbeddingRateLimitError on exhaustion."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 429
    error_429 = HfHubHTTPError("Rate limit reached", response=mock_response)
    mock_client.feature_extraction = AsyncMock(side_effect=error_429)

    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(EmbeddingRateLimitError, match="rate limit reached"):
            await service.embed_text("Test query")

        # Configured with max_retries=2, so total calls = 1 initial + 2 retries = 3 calls
        assert mock_client.feature_extraction.call_count == 3
        assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_authentication_error_not_retried(custom_settings: Settings) -> None:
    """Verify HTTP 401 unauthorized raises EmbeddingAuthenticationError immediately without retrying."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    error_401 = HfHubHTTPError("Invalid token", response=mock_response)
    mock_client.feature_extraction = AsyncMock(side_effect=error_401)

    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(EmbeddingAuthenticationError, match="API token is invalid"):
            await service.embed_text("Test query")

        # Must not retry permanent authentication failure
        assert mock_client.feature_extraction.call_count == 1
        assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_timeout_retry_and_exhaustion(custom_settings: Settings) -> None:
    """Verify request timeout is retried and raises EmbeddingTimeoutError on exhaustion."""
    mock_client = MagicMock()
    mock_client.feature_extraction = AsyncMock(side_effect=InferenceTimeoutError("Connection timed out"))

    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(EmbeddingTimeoutError, match="timed out"):
            await service.embed_text("Test query")

        assert mock_client.feature_extraction.call_count == 3


@pytest.mark.asyncio
async def test_client_close(custom_settings: Settings) -> None:
    """Verify close() releases the underlying client connection cleanly."""
    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    # Pass client into service
    service = HuggingFaceEmbeddingService(settings=custom_settings, client=mock_client)
    service._owns_client = True
    await service.close()

    mock_client.close.assert_called_once()

