"""Hugging Face Inference Providers implementation of text embedding service."""

import asyncio
import logging
from typing import Any, List, Optional
import numpy as np

from huggingface_hub import AsyncInferenceClient
from huggingface_hub.errors import (
    HfHubHTTPError,
    InferenceTimeoutError,
    RepositoryNotFoundError,
)

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    EmbeddingAuthenticationError,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingRateLimitError,
    EmbeddingServiceUnavailableError,
    EmbeddingTimeoutError,
)
from app.embeddings.base import BaseEmbeddingService

logger = logging.getLogger(__name__)


class HuggingFaceEmbeddingService(BaseEmbeddingService):
    """Generates embeddings using hosted Hugging Face Inference Providers.

    Default model: BAAI/bge-small-en-v1.5 (384 dimensions).
    Uses official huggingface_hub.AsyncInferenceClient.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[AsyncInferenceClient] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._model_name = self._settings.EMBEDDING_MODEL
        self._dimension = self._settings.EMBEDDING_DIMENSION
        self._batch_size = self._settings.EMBEDDING_BATCH_SIZE
        self._timeout = self._settings.EMBEDDING_TIMEOUT
        self._max_retries = self._settings.EMBEDDING_MAX_RETRIES

        token = self._settings.HF_TOKEN if self._settings.HF_TOKEN.strip() else None
        self._client = client or AsyncInferenceClient(
            token=token,
            timeout=self._timeout,
        )
        self._owns_client = client is None

        logger.info(
            "Initialized HuggingFaceEmbeddingService with model=%s, dimension=%d, batch_size=%d",
            self._model_name,
            self._dimension,
            self._batch_size,
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed_text(self, text: str) -> List[float]:
        """Generate an embedding vector for a single non-empty text string."""
        if not text or not text.strip():
            raise ValueError("Input text for embedding must not be empty or whitespace only.")

        embeddings = await self.embed_batch([text])
        if not embeddings or len(embeddings) != 1:
            raise EmbeddingError("Failed to obtain embedding from provider for single text input.")
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of text strings with chunked batching."""
        if not texts:
            return []

        # Validate each item
        for idx, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Input text at index {idx} must be a non-empty string.")

        all_embeddings: List[List[float]] = []

        # Process in batches to respect provider payload limits
        for start_idx in range(0, len(texts), self._batch_size):
            chunk = texts[start_idx : start_idx + self._batch_size]
            batch_result = await self._call_with_retries(chunk)
            all_embeddings.extend(batch_result)

        return all_embeddings

    async def _call_with_retries(self, texts: List[str]) -> List[List[float]]:
        """Execute feature-extraction with bounded exponential backoff retries."""
        attempt = 0
        backoff_delay = 1.0

        while attempt <= self._max_retries:
            attempt += 1
            try:
                # Call hosted feature_extraction API
                raw_response = await self._client.feature_extraction(
                    text=texts,
                    model=self._model_name,
                )
                return self._parse_and_validate_response(raw_response, expected_count=len(texts))

            except RepositoryNotFoundError as exc:
                logger.error("Configured embedding model not found: %s", self._model_name)
                raise EmbeddingError(f"Embedding model '{self._model_name}' not found on Hugging Face Hub.") from exc

            except HfHubHTTPError as exc:
                status_code = getattr(exc.response, "status_code", None) if hasattr(exc, "response") else None

                # Non-retryable authentication / permissions errors
                if status_code in (401, 403):
                    logger.error("Hugging Face authentication failed with HTTP %s", status_code)
                    raise EmbeddingAuthenticationError(
                        "Hugging Face API token is invalid, unauthorized, or missing.",
                        details={"status_code": status_code},
                    ) from exc

                # Non-retryable client errors
                if status_code and 400 <= status_code < 429:
                    logger.error("Hugging Face API returned client error HTTP %s", status_code)
                    raise EmbeddingError(
                        f"Hugging Face API client error (HTTP {status_code}).",
                        details={"status_code": status_code},
                    ) from exc

                # Retryable: Rate limit (429)
                if status_code == 429:
                    if attempt > self._max_retries:
                        logger.error("Hugging Face rate limit exceeded and max retries exhausted (%d).", self._max_retries)
                        raise EmbeddingRateLimitError(
                            "Hugging Face API rate limit reached. Retries exhausted.",
                            details={"status_code": 429, "attempts": attempt},
                        ) from exc
                    logger.warning(
                        "Hugging Face rate limit (429) hit. Backing off for %.2fs (attempt %d/%d)...",
                        backoff_delay,
                        attempt,
                        self._max_retries,
                    )
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2.0
                    continue

                # Retryable: Model loading or server error (503 / 504 / 500)
                if status_code and status_code >= 500:
                    if attempt > self._max_retries:
                        logger.error("Hugging Face server error (HTTP %s) after %d retries.", status_code, self._max_retries)
                        raise EmbeddingServiceUnavailableError(
                            f"Hugging Face server error (HTTP {status_code}). Retries exhausted.",
                            details={"status_code": status_code, "attempts": attempt},
                        ) from exc
                    logger.warning(
                        "Hugging Face server error (HTTP %s). Backing off for %.2fs (attempt %d/%d)...",
                        status_code,
                        backoff_delay,
                        attempt,
                        self._max_retries,
                    )
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2.0
                    continue

                # Any other HfHubHTTPError
                if attempt > self._max_retries:
                    raise EmbeddingError(f"Hugging Face API error: {exc}") from exc
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

            except (InferenceTimeoutError, asyncio.TimeoutError) as exc:
                if attempt > self._max_retries:
                    logger.error("Embedding request timed out after %d retries.", self._max_retries)
                    raise EmbeddingTimeoutError(
                        f"Embedding request timed out after {self._timeout}s.",
                        details={"timeout": self._timeout, "attempts": attempt},
                    ) from exc
                logger.warning("Embedding request timed out. Retrying in %.2fs (attempt %d/%d)...", backoff_delay, attempt, self._max_retries)
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

            except Exception as exc:
                # If already an embedding error, re-raise directly
                if isinstance(exc, (EmbeddingDimensionMismatchError, EmbeddingError)):
                    raise exc
                logger.error("Unexpected error during embedding extraction: %s", type(exc).__name__)
                if attempt > self._max_retries:
                    raise EmbeddingError(f"Unexpected error communicating with embedding provider: {type(exc).__name__}") from exc
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

        raise EmbeddingError("Embedding retries exhausted without a response.")

    def _parse_and_validate_response(self, raw_response: Any, expected_count: int) -> List[List[float]]:
        """Normalize raw array or list response, validate dimensions, and convert to Python float lists."""
        if raw_response is None:
            raise EmbeddingError("Provider returned an empty response.")

        # Convert numpy array to Python list
        if isinstance(raw_response, np.ndarray):
            data = raw_response.tolist()
        elif isinstance(raw_response, list):
            data = raw_response
        else:
            raise EmbeddingError(f"Unexpected embedding response type: {type(raw_response).__name__}")

        # If data is 1D (single vector) and expected_count == 1, wrap it
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], (int, float)):
            if expected_count == 1:
                data = [data]
            else:
                raise EmbeddingDimensionMismatchError(
                    f"Expected {expected_count} vectors, but received a 1D vector of length {len(data)}."
                )

        if not isinstance(data, list) or len(data) != expected_count:
            raise EmbeddingError(f"Expected {expected_count} embedding vectors, but received {len(data) if isinstance(data, list) else 0}.")

        validated: List[List[float]] = []
        for idx, vec in enumerate(data):
            if not isinstance(vec, list):
                raise EmbeddingError(f"Vector at index {idx} is not a valid list.")
            if len(vec) != self._dimension:
                raise EmbeddingDimensionMismatchError(
                    f"Vector dimension mismatch at index {idx}: expected {self._dimension}, got {len(vec)}."
                )
            validated.append([float(val) for val in vec])

        return validated

    async def close(self) -> None:
        """Close AsyncInferenceClient if owned by this service."""
        if self._owns_client and hasattr(self._client, "close"):
            try:
                await self._client.close()
                logger.debug("Closed Hugging Face AsyncInferenceClient.")
            except Exception as exc:
                logger.warning("Error closing Hugging Face client: %s", exc)

