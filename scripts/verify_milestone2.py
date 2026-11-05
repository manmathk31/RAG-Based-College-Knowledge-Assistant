"""Verification script for Milestone 2: Hosted Embeddings and Qdrant Vector Store."""

import asyncio
import os
import sys

# Ensure backend is on sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import get_settings
from app.embeddings.base import BaseEmbeddingService
from app.embeddings.huggingface import HuggingFaceEmbeddingService
from app.vector_store.base import BaseVectorStore
from app.vector_store.qdrant import QdrantVectorStore


async def verify_milestone2() -> int:
    print("=" * 70)
    print("Verifying Milestone 2: Hosted Embeddings & Qdrant Vector Store")
    print("=" * 70)

    settings = get_settings()

    # 1. Verify Configuration
    print(f"\n1. Verifying Settings:")
    print(f"   [OK] Embedding Provider:   {settings.EMBEDDING_PROVIDER}")
    print(f"   [OK] Embedding Model:      {settings.EMBEDDING_MODEL}")
    print(f"   [OK] Embedding Dimension:  {settings.EMBEDDING_DIMENSION}")
    print(f"   [OK] Qdrant Collection:    {settings.QDRANT_COLLECTION_NAME}")
    print(f"   [OK] Qdrant Timeout:       {settings.QDRANT_TIMEOUT}s")

    assert settings.EMBEDDING_DIMENSION == 384, "Embedding dimension must be 384 for BAAI/bge-small-en-v1.5"

    # 2. Verify Interfaces and Subclasses
    print(f"\n2. Verifying Class Contracts:")
    assert issubclass(HuggingFaceEmbeddingService, BaseEmbeddingService), "HuggingFaceEmbeddingService must implement BaseEmbeddingService"
    print(f"   [OK] HuggingFaceEmbeddingService implements BaseEmbeddingService")

    assert issubclass(QdrantVectorStore, BaseVectorStore), "QdrantVectorStore must implement BaseVectorStore"
    print(f"   [OK] QdrantVectorStore implements BaseVectorStore")

    # 3. Verify Local Instantiation
    print(f"\n3. Verifying Local Service Instantiation:")
    emb_svc = HuggingFaceEmbeddingService(settings=settings)
    assert emb_svc.dimension == 384
    assert emb_svc.model_name == "BAAI/bge-small-en-v1.5"
    print(f"   [OK] Embedding service ready (model={emb_svc.model_name}, dim={emb_svc.dimension})")

    qdrant_store = QdrantVectorStore(settings=settings)
    print(f"   [OK] Qdrant vector store adapter ready")

    # 4. Optional Live Connectivity Check
    print(f"\n4. Checking Live External Credentials:")
    hf_token_configured = bool(settings.HF_TOKEN and settings.HF_TOKEN.strip() and not settings.HF_TOKEN.startswith("your-"))
    qdrant_configured = bool(settings.QDRANT_URL and settings.QDRANT_URL.strip() and not settings.QDRANT_URL.startswith("https://your-"))

    if hf_token_configured:
        print("   [*] HF_TOKEN found. Attempting live embedding test...")
        try:
            vec = await emb_svc.embed_text("College library regulations test query")
            print(f"   [SUCCESS] Live Hugging Face API call succeeded! Vector dimension: {len(vec)}")
        except Exception as e:
            print(f"   [WARNING] Live Hugging Face API call failed: {e}")
    else:
        print("   [-] HF_TOKEN not configured in .env. Live Hugging Face connectivity not executed.")

    if qdrant_configured:
        print("   [*] QDRANT_URL found. Attempting live ping...")
        try:
            connected = await qdrant_store.ping()
            if connected:
                print(f"   [SUCCESS] Live Qdrant Cloud cluster ping succeeded!")
            else:
                print(f"   [WARNING] Live Qdrant Cloud ping returned False.")
        except Exception as e:
            print(f"   [WARNING] Live Qdrant connection check failed: {e}")
    else:
        print("   [-] QDRANT_URL not configured in .env. Live Qdrant connectivity not executed.")

    await emb_svc.close()
    await qdrant_store.close()

    print("\n" + "=" * 70)
    print("Milestone 2 Scaffolding & Contract Verification: PASSED")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(verify_milestone2()))

