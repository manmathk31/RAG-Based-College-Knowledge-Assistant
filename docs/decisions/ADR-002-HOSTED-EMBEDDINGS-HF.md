# ADR-002: Hosted Embeddings via Hugging Face Inference Providers

- **Status**: ACCEPTED
- **Date**: 2026-11-05
- **Deciders**: Senior Backend Engineer, Project Architecture Lead

---

## 1. Context & Problem Statement

In the initial architecture ([ADR-001](ADR-001-INITIAL-ARCHITECTURE.md)), Google Gemini API was tentatively selected for both embeddings and generation. However, evaluating domain-specific retrieval needs for English-language academic documents highlighted the following:

1. **Model Specialization**: `BAAI/bge-small-en-v1.5` is an industry-standard, top-performing compact embedding model specifically fine-tuned for English semantic search, passage retrieval, and semantic similarity.
2. **Compact Dimensionality**: At 384 dimensions (compared to 768 or 1536), `bge-small-en-v1.5` cuts vector storage and indexing memory in Qdrant Cloud by 50%, enabling higher chunk capacity within free-tier cluster limits while retaining state-of-the-art MTEB retrieval performance.
3. **Provider Decoupling**: Utilizing Hugging Face Inference Providers prevents hard vendor lock-in to a single ecosystem, separating the embedding generation tier from the future answer generation LLM (Google Gemini).

---

## 2. Decision

1. Adopt **Hugging Face Inference Providers** as the primary hosted embedding provider.
2. Standardize on **`BAAI/bge-small-en-v1.5`** as the default embedding model, with **384 vector dimensions** and Cosine similarity.
3. Implement `HuggingFaceEmbeddingService` using the official `huggingface_hub.AsyncInferenceClient` targeting the `feature-extraction` task.
4. Keep the provider, model identifier, batch size, and dimensions fully configurable via environment variables (`HF_TOKEN`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`).

---

## 3. Important Consistency Rule & Migration Invariants

- The same configured embedding model and preprocessing must be used for document chunk ingestion and user query retrieval.
- Mixing embeddings from incompatible models or dimensions within the same Qdrant collection is strictly prohibited.
- `QdrantVectorStore.validate_collection` enforces strict checks on vector dimensionality (384) and distance metric (Cosine), failing clearly if an existing collection has a conflicting configuration.
- Future model changes will require re-indexing documents under a new collection name or clean migration.

---

## 4. Operational Trade-offs & Free-Tier Limitations

- **Rate Limits**: Hugging Face serverless free-tier inference is subject to rate limits (HTTP 429). The implementation introduces bounded exponential backoff retries (`EMBEDDING_MAX_RETRIES=3`).
- **Cold Starts**: Shared serverless endpoints may take several seconds on cold starts (HTTP 503). Retries gracefully wait for model loading.
- **Quota Boundaries**: The free tier is not permanently unlimited. For production deployments with thousands of document chunks, a Hugging Face Pro subscription or dedicated Inference Endpoint is recommended.

---

## 5. Consequences

- `backend/requirements.txt` updated to include `huggingface_hub>=0.25.0` and `numpy>=2.0.0`.
- Qdrant Cloud collections configured with `size=384` and `distance=Cosine`.
- LLM answer generation remains scheduled for Google Gemini (`gemini-2.5-flash`) in Milestone 7.

