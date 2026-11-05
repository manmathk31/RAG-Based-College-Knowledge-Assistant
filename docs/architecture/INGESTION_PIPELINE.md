# Ingestion Pipeline Specification

> **Status Notice**: All Stages 1 through 7 (Upload Validation, Supabase Registration, Extraction, Selective OCR, Structure-Aware Chunking, Batch Embeddings, Qdrant Indexing, Full-Text Keyword Indexing, and Version Lifecycle) are **FULLY IMPLEMENTED** as of Milestone 5.

---

## 1. Objectives & Principles

The ingestion pipeline is responsible for parsing unstructured institutional documents, detecting and transcribing scanned media, chunking text without destroying grammatical boundaries, computing vector embeddings, and indexing chunks into Qdrant Cloud.

### Core Principles:
1. **Zero Data Loss**: Every chunk must retain document traceability (document name, page number, chunk index, section heading, document version).
2. **Selective OCR**: Never run OCR indiscriminately on high-fidelity digital PDFs due to latency and compute overhead; run OCR strictly when selectable text is absent (< 50 chars).
3. **Page Boundary Integrity**: Avoid combining content from different pages into single chunks so source citation cards in the chatbot display precise, verifiable page references.
4. **Heading Context Propagation**: Preserve document heading hierarchy by attaching section headings to chunks.
5. **Exact Idempotency**: Re-uploading an identical file (`content_hash`) skips redundant embedding and indexing, returning the existing record with `action="duplicate_skipped"`.
6. **Managed Versioning**: Uploading different content with an existing filename increments the version (`v2, v3`), activates the new version, deactivates the old version, and purges superseded vectors from Qdrant.
7. **Ephemeral Storage**: Uploaded PDF and DOCX binaries are streamed to temporary files, processed, and deleted immediately in `finally` blocks. Original binaries are never permanently stored.
8. **Compensating Consistency**: Any failure during extraction, embedding, or indexing rolls back partially upserted vectors from Qdrant and records failure diagnostic status in Supabase.

---

## 2. Ingestion Stages & Architecture

```
[Raw File Upload]
       │
       ▼
[Stage 1: Validation & Streaming Staging] ─── (Signature check, Size check, SHA-256 hash)
       │
       ▼
[Stage 2: Supabase Registration & Deduplication] ─── (Duplicate check, Version increment, Status="processing")
       │
       ▼
[Stage 3: Format-Specific Extraction] ─── (PyMuPDF for PDF, python-docx for DOCX, Selective OCR)
       │
       ▼
[Stage 4: Structure-Aware Chunking] ─── (~600 tokens target, ~100 tokens overlap, tiktoken)
       │
       ▼
[Stage 5: Batch Embedding Generation] ─── (Hugging Face BAAI/bge-small-en-v1.5, 384-dim, batches <= 32)
       │
       ▼
[Stage 6: Qdrant Vector & Payload Indexing] ─── (Cosine distance, HNSW Index, Version payload tag)
       │
       ▼
[Stage 7: Supabase Activation & Cleanup] ─── (Status="completed", is_active=true, purge old vectors)
```

---

## 3. Detailed Stage Specifications

### Stage 1: Validation, Hashing & Ephemeral Staging
- **File Signatures**: Validated via magic bytes inspection:
  - PDF: Starts with `%PDF-` (`b"%PDF-"`).
  - DOCX: Starts with ZIP header (`b"PK\x03\x04"`) and contains `word/document.xml`.
- **Upload Constraints**: Enforces maximum upload size (`MAX_UPLOAD_SIZE_BYTES`, default: 50 MB).
- **Temporary Storage**: Streamed to local temporary files created with `tempfile.mkstemp()`. In both success and failure paths, `staged.cleanup()` deletes the temporary file.

### Stage 2: Supabase Metadata Registration
- Query for existing completed record with matching `content_hash` and `is_active=True`. If found, return immediately without re-embedding.
- If same `normalized_filename` has existing records, determine new version (`max(version) + 1`).
- Insert new `DocumentModel` record with `status="processing"`, `is_active=False`, `processing_started_at=utcnow()`.

### Stage 3: Format Extraction & Selective OCR
- **PDF Extraction (`PDFExtractor` via PyMuPDF)**: Extracts layout text blocks page-by-page. Pages with < 50 characters trigger selective OCR.
- **Selective OCR (`TesseractOCRExtractor` via PyTesseract)**: Renders scanned page at 300 DPI and transcribes text.
- **DOCX Extraction (`DOCXExtractor` via `python-docx`)**: Traverses body elements preserving paragraph order, headings, and formatting tables as Markdown tables.

### Stage 4: Structure-Aware Chunking (`StructureAwareChunker`)
- Counts tokens via `tiktoken` (`cl100k_base`).
- Flushes on page boundary transitions to ensure 1:1 page citation integrity.
- Preserves nearest heading hierarchy in `section_heading`.

### Stage 5: Batch Embedding Generation (`HuggingFaceEmbeddingService`)
- Embeds chunk texts in batches of up to 32 using hosted Hugging Face Inference Providers (`BAAI/bge-small-en-v1.5`).
- Generates 384-dimensional normalized dense vectors with bounded exponential backoff retries.

### Stage 6: Vector Indexing & Keyword Full-Text Search Ingestion
- **Qdrant Vector Indexing (`QdrantVectorStore`)**: Upserts points into collection with payloads containing: `document_id`, `document_version`, `document_name`, `page_number`, `chunk_index`, `section`, `content`, `is_active`.
- **Supabase Keyword Search Ingestion (`DocumentChunkModel`)**: Indexes chunk IDs, page numbers, section titles, and PostgreSQL `search_vector` (`func.to_tsvector('english', chunk.content)`) with GIN indexing into `document_chunks`. Full chunk text is NOT duplicated in PostgreSQL (canonical chunk text remains in Qdrant).

### Stage 7: Supabase Activation & Compensating Cleanup
- Updates Supabase record: `status="completed"`, `is_active=True`, `chunk_count=len(chunks)`, `processing_completed_at=utcnow()`.
- If new version (`v > 1`), deactivates previous versions (`is_active=False`) and purges their points from Qdrant via `delete_by_document_id`.
- On error at any point: deletes partial vectors from Qdrant, marks Supabase record `status="failed"` with diagnostic error message.

---

## 4. Implementation Status Matrix

| Component | Implementation Class | Current Implementation Status |
|---|---|---|
| Metadata Database | Supabase PostgreSQL via SQLAlchemy 2.0 & Alembic | 🟢 Implemented (Milestone 4) |
| Ephemeral File Staging | `StagedUpload` (`backend/app/ingestion/orchestrator.py`) | 🟢 Implemented (Milestone 4) |
| Ingestion Orchestrator | `DocumentIngestionOrchestrator` (`backend/app/ingestion/orchestrator.py`) | 🟢 Implemented (Milestone 4) |
| Document Management APIs | `/api/v1/documents/*` (`backend/app/api/v1/documents.py`) | 🟢 Implemented (Milestone 4) |
| Versioning & Deduplication | Content hashing & version deactivation | 🟢 Implemented (Milestone 4) |
| Compensating Rollback | Automatic Qdrant vector deletion on failure | 🟢 Implemented (Milestone 4) |
| PDF Text Extractor | `PDFExtractor` (`backend/app/ingestion/extractors/pdf.py`) | 🟢 Implemented (Milestone 3) |
| DOCX Text Extractor | `DOCXExtractor` (`backend/app/ingestion/extractors/docx.py`) | 🟢 Implemented (Milestone 3) |
| Selective OCR | `TesseractOCRExtractor` (`backend/app/ingestion/extractors/ocr.py`) | 🟢 Implemented (Milestone 3) |
| Structure-Aware Chunker | `StructureAwareChunker` (`backend/app/ingestion/chunker.py`) | 🟢 Implemented (Milestone 3) |
| Hosted Embeddings | `HuggingFaceEmbeddingService` (`backend/app/embeddings/`) | 🟢 Implemented (Milestone 2) |
| Qdrant Upsert & Search | `QdrantVectorStore` (`backend/app/vector_store/`) | 🟢 Implemented (Milestone 2) |

