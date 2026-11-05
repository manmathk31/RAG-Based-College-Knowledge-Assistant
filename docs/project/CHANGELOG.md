# Changelog

All notable changes to the `RAG-Based-College-Knowledge-Assistant` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Milestone 2: Hosted Embeddings & Qdrant Cloud Vector Store**:
  - `BaseEmbeddingService` interface and `HuggingFaceEmbeddingService` adapter using `huggingface_hub.AsyncInferenceClient`.
  - Configured default model: `BAAI/bge-small-en-v1.5` (384 dimensions) targeting `feature-extraction`.
  - Sub-batching support (`EMBEDDING_BATCH_SIZE=32`) and bounded exponential backoff retries for HTTP 429 / 503 / timeouts.
  - Strict vector dimension validation and sensible handling of empty/whitespace inputs.
  - `QdrantVectorStore` adapter implementing `BaseVectorStore` with `AsyncQdrantClient`.
  - Qdrant collection initialization (Cosine distance, 384 dimensions) and keyword payload index on `document_id`.
  - Collection configuration validation preventing silent overwrites or dimension mismatches.
  - Vector operations: batch upsert with deterministic UUID5 normalization, filtered vector search, document deletion by `document_id`.
  - Domain exceptions: `EmbeddingError`, `EmbeddingDimensionMismatchError`, `EmbeddingRateLimitError`, `VectorStoreOperationError`, etc.
  - FastAPI lifespan integration for non-blocking Qdrant and Embedding client lifecycle.
  - Readiness endpoint `GET /api/v1/health/ready` reporting dependency readiness safely.
  - Architecture Decision Record: `ADR-002-HOSTED-EMBEDDINGS-HF.md`.
  - Comprehensive unit test suites: `test_embeddings.py` (8 passed), `test_qdrant.py` (9 passed), `test_health.py` (3 passed).
  - Milestone verification script: `scripts/verify_milestone2.py`.
  - Root `AGENTS.md` governing persistent coding guidelines, invariants, testing policy, and AI agent rules.
  - Architecture documentation: `SYSTEM_ARCHITECTURE.md`, `DATA_FLOW.md`, `INGESTION_PIPELINE.md`.
  - Architecture Decision Records: `ADR-001-INITIAL-ARCHITECTURE.md` capturing 10 key technical choices.
  - Development and testing documentation: `DEVELOPMENT_GUIDE.md`, `CODING_CONVENTIONS.md`, `TESTING_STRATEGY.md`.
  - Project tracking: `PROJECT_STATUS.md`, `IMPLEMENTATION_PLAN.md`, `CHANGELOG.md`.
  - Environment templates: root `.env.example`, `backend/.env.example`.
  - Monorepo directory structure for backend and dual frontends (`frontend/user-app`, `frontend/admin-app`).
  - Minimal local Docker Compose configuration (`docker-compose.yml`).
  - Backend scaffold: FastAPI application, Pydantic settings, health check endpoint (`/api/v1/health`), and structured logging.
  - Frontend scaffolds: Independent React + TypeScript + Vite + Tailwind CSS setups for User and Admin apps.
  - Verification & validation pass: Successfully verified backend imports, executed Pytest suite for health endpoints, verified live Uvicorn HTTP health check, and built both frontend bundles (`tsc && vite build`).
