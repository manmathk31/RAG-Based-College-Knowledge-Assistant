"""FastEmbed local implementation of text embedding service using ONNX runtime."""

import asyncio
import logging
from typing import List, Optional

from fastembed import TextEmbedding

from app.core.config import Settings, get_settings
from app.core.exceptions import EmbeddingError
from app.embeddings.base import BaseEmbeddingService

logger = logging.getLogger(__name__)


class FastEmbedEmbeddingService(BaseEmbeddingService):
    """Generates embeddings locally using fastembed ONNX runtime.

    Default model: BAAI/bge-small-en-v1.5 (384 dimensions).
    Runs completely offline on CPU with zero API costs and zero external dependencies.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        model: Optional[TextEmbedding] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._model_name = self._settings.EMBEDDING_MODEL
        self._dimension = self._settings.EMBEDDING_DIMENSION
        self._model = model or TextEmbedding(model_name=self._model_name)

        logger.info(
            "Initialized FastEmbedEmbeddingService with model=%s (local ONNX, dimension=%d)",
            self._model_name,
            self._dimension,
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _embed_sync(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        # FastEmbed model.embed returns a generator of numpy arrays
        bs = batch_size or getattr(self._settings, "EMBEDDING_BATCH_SIZE", 8)
        embeddings_gen = self._model.embed(texts, batch_size=bs)
        res = [list(vec.astype(float)) for vec in embeddings_gen]
        import gc
        gc.collect()
        return res

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text string."""
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty or whitespace-only text.")

        results = self._embed_sync([text])
        return results[0]

    # Backward-compatible alias
    embed_single = embed_text

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Generate embedding vectors for a batch of text strings."""
        if not texts:
            return []

        # Replace any empty strings with single whitespace so fastembed processes full length
        cleaned = [t if t and t.strip() else " " for t in texts]
        return self._embed_sync(cleaned, batch_size=batch_size)

    async def close(self) -> None:
        """Release any resources."""
        self._model = None
