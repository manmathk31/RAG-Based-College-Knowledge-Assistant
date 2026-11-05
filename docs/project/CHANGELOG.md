# Changelog

All notable changes to the `RAG-Based-College-Knowledge-Assistant` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Milestone 5: Final Backend Completion (Hybrid RAG, Chat API, Frontend Handoff)**:
  - **Hybrid Retrieval Engine** (`backend/app/retrieval/`):
    - `DenseRetriever`: Qdrant Cloud semantic vector search using Hugging Face embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions) with active document version filtering (`is_active=True`).
    - `KeywordRetriever`: PostgreSQL Full-Text Search via `websearch_to_tsquery` and `ts_rank_cd` against `document_chunks` GIN index; canonical chunk text retrieved from Qdrant via `get_points_by_ids` without duplicating text in relational storage.
    - `reciprocal_rank_fusion`: Rank aggregation ($k=60$) combining dense semantic rankings and sparse keyword rankings.
    - `ContextBuilder`: Context assembly with token budgeting (`MAX_CONTEXT_TOKENS=2000` via `tiktoken`), near-duplicate chunk deduplication, and numbered citation markers `[1]`, `[2]`.
    - `HybridRetrievalEngine`: Orchestrates retrieval pipeline with automatic graceful degradation (dense-only on Supabase outage, keyword-only on Qdrant outage, honest 503 if both fail).
  - **Database Migration 002**:
    - Created `document_chunks` table storing `chunk_id`, `document_id` (foreign key to `documents.id` with cascade delete), `document_version`, `page_number`, `section_title`, `is_active`, and `search_vector` (`TSVECTOR`).
    - GIN index on `search_vector` for fast inverted index lookups.
  - **Gemini Answer Generation Service** (`backend/app/generation/`):
    - `GeminiGenerationService` implementing official Google Gen AI SDK (`google-genai` async client) using `gemini-2.5-flash`.
    - Strict grounding system instructions enforcing factual source attribution with `[1]`, `[2]` markers, zero hallucinations, and honest uncertainty disclosures.
    - Robust exponential backoff with jitter via `tenacity` handling HTTP 429 rate limits, 503 service unavailabilities, and timeouts.
  - **User Chat API** (`backend/app/api/v1/chat.py`):
    - `POST /api/v1/chat` and backward-compatible alias `POST /api/v1/chat/query`.
    - Accepts both `{"message": "..."}` and `{"question": "..."}` inputs.
    - Zero-downtime dense retrieval fallback when Supabase connection drops.
    - Structured response schema with `answer`, `sources`, `retrieval_mode`, and `request_id`.
  - **Retrieval Evaluation Benchmark** (`backend/tests/test_retrieval_evaluation.py`):
    - Deterministic college query evaluation benchmark proving Hybrid RAG achieves Recall@3=1.00 and MRR=1.00 vs Dense-Only MRR=0.70.
  - **Frontend Integration Guide** (`docs/frontend/API_INTEGRATION_GUIDE.md`):
    - 14-section comprehensive handoff manual covering backend architecture, base URLs, Chat & Admin API contracts, citation UI patterns, TypeScript types, `fetch` client code, error handling, CORS, and local startup.
  - Comprehensive unit and integration test suite expanding test coverage to 96 passing tests across all modules.
- **Milestone 4: Supabase Metadata Database & End-to-End Document Ingestion**:
  - Authoritative document metadata persistence using **Supabase PostgreSQL** via SQLAlchemy 2.0 with asynchronous `asyncpg` driver.
  - Database declarative models (`DocumentModel`) with comprehensive fields: `id`, `original_filename`, `normalized_filename`, `file_type`, `file_size`, `content_hash`, `document_version`, `status`, `chunk_count`, `is_active`, `created_at`, `updated_at`, `processing_started_at`, `processing_completed_at`, `error_message`.
  - Composite unique constraint `(normalized_filename, document_version)` and indexes on `content_hash`, `normalized_filename`, `status`, and `is_active`.
  - Alembic asynchronous database migrations with initial migration `001_create_documents`.
  - Ephemeral file upload validation (`StagedUpload`): streaming upload with strict file signature sniffing (`%PDF-` for PDF, ZIP structure and `word/document.xml` for DOCX), file size limits (`MAX_UPLOAD_SIZE_BYTES=50MB`), and guaranteed temporary file cleanup in `finally` blocks.
  - End-to-end ingestion orchestrator (`DocumentIngestionOrchestrator`):
    - Exact duplicate detection: avoids re-embedding or re-indexing if identical content hash exists with `status=completed` and `is_active=true`.
    - Monotonic versioning: auto-increments document version (`v2, v3`) when the same filename is uploaded with different content.
    - Atomic activation: new version is activated in Supabase only after all chunks are indexed in Qdrant, automatically deactivating previous versions.
    - Compensating rollback: deletes partially indexed vectors from Qdrant and records diagnostic failure messages in Supabase on pipeline errors.
    - Purges superseded historical vectors from Qdrant upon successful new version activation.
  - Administrative REST API endpoints under `/api/v1/documents`:
    - `POST /api/v1/documents`: upload and process document with admin protection (`X-Admin-Secret`).
    - `GET /api/v1/documents`: list documents with pagination (`skip`, `limit`) and filters (`status`, `is_active`).
    - `GET /api/v1/documents/{document_id}`: retrieve document metadata and processing lifecycle status.
    - `POST /api/v1/documents/{document_id}/retry`: retry ingestion of failed documents with re-uploaded file.
    - `DELETE /api/v1/documents/{document_id}`: delete document and purge all associated version vectors from Qdrant.
  - Architecture Decision Record: `ADR-003-SUPABASE-METADATA-STORE.md`.
  - Health check readiness enhancement: `/api/v1/health/ready` reports database connectivity and configuration status.
  - Unit and integration tests covering database models, upload validation, orchestrator lifecycle, duplicate handling, rollback, and API endpoints (68 passed).
  - Milestone verification script: `scripts/verify_milestone4.py`.
- **Milestone 3: Document Extraction and Structure-Aware Chunking**:
  - Pydantic models for extraction hierarchy: `ExtractedBlock`, `ExtractedPage`, `ExtractedDocument`, and `DocumentChunk` with `to_qdrant_payload()` helper.
  - Abstract extraction contract `BaseExtractor`.
  - `PDFExtractor` using PyMuPDF (`fitz`) with block structure detection, 1:1 page correlation, empty page handling, and scanned page threshold detection (< 50 chars).
  - Selective OCR integration via `TesseractOCRExtractor` using `pytesseract` and Pillow, with availability detection (`is_available()`) and clear error messaging on missing binaries (`TesseractNotFoundError`).
  - `DOCXExtractor` using `python-docx` traversing XML body elements in document order, preserving headings (`Heading 1-6`), and converting tables into markdown formatting.
  - `StructureAwareChunker` supporting token-based chunking with `tiktoken` (`cl100k_base`), target 600 tokens, 100 overlap, heading context preservation, and page boundary flushing.
  - `DocumentIngestionService` coordinating format validation, extraction, and chunking.
  - FastAPI lifecycle integration and dependency injection (`get_ingestion_service`).
  - Domain exceptions: `IngestionError`, `UnsupportedFileFormatError`, `CorruptedDocumentError`, `EmptyDocumentError`, `OCRError`, `TesseractNotFoundError`, `ChunkingError`.
  - Comprehensive unit test suites: `test_pdf_extractor.py` (5 passed), `test_docx_extractor.py` (4 passed), `test_chunker.py` (6 passed), `test_ingestion_service.py` (3 passed) — total test suite 38/38 passed.
  - Milestone verification script `scripts/verify_milestone3.py`.
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
