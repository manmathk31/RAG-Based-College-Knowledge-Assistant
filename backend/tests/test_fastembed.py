"""Unit tests for FastEmbed local embedding service."""

import pytest
from app.core.config import Settings
from app.core.exceptions import EmbeddingError
from app.embeddings.fastembed import FastEmbedEmbeddingService


@pytest.mark.asyncio
async def test_fastembed_single_text_and_dimension():
    settings = Settings(
        EMBEDDING_PROVIDER="fastembed",
        EMBEDDING_MODEL="BAAI/bge-small-en-v1.5",
        EMBEDDING_DIMENSION=384,
    )
    service = FastEmbedEmbeddingService(settings=settings)
    assert service.dimension == 384
    assert service.model_name == "BAAI/bge-small-en-v1.5"

    vec = await service.embed_text("What is the hostel curfew?")
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)
    await service.close()


@pytest.mark.asyncio
async def test_fastembed_batch_texts():
    settings = Settings(
        EMBEDDING_PROVIDER="fastembed",
        EMBEDDING_MODEL="BAAI/bge-small-en-v1.5",
        EMBEDDING_DIMENSION=384,
    )
    service = FastEmbedEmbeddingService(settings=settings)
    texts = [
        "First document paragraph.",
        "Second document paragraph.",
        "Third document paragraph.",
    ]
    vectors = await service.embed_batch(texts)
    assert len(vectors) == 3
    for vec in vectors:
        assert len(vec) == 384
    await service.close()


@pytest.mark.asyncio
async def test_fastembed_empty_text_raises_error():
    service = FastEmbedEmbeddingService()
    with pytest.raises(EmbeddingError):
        await service.embed_text("")
    with pytest.raises(EmbeddingError):
        await service.embed_text("   ")
    await service.close()
