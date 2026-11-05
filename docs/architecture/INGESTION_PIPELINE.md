# Ingestion Pipeline Specification

> **Status Notice**: This document specifies the planned architecture and engineering requirements for the document ingestion pipeline. **The pipeline is currently in the DESIGN phase and is NOT yet implemented.**

---

## 1. Objectives & Principles

The ingestion pipeline is responsible for parsing unstructured institutional documents, detecting and transcribing scanned media, chunking text without destroying grammatical boundaries, computing vector embeddings, and indexing chunks into Qdrant Cloud.

### Core Principles:
1. **Zero Data Loss**: Every chunk must retain document traceability (document name, page number, chunk index).
2. **Selective OCR**: Never run OCR indiscriminately on high-fidelity digital PDFs due to latency and compute overhead; run OCR strictly when text streams are absent or corrupted.
3. **Idempotency**: Processing the same document twice must not create duplicate vectors in Qdrant.
4. **Resilience**: A failure in one page or chunk batch must be captured gracefully without leaving orphan data in the vector database.

---

## 2. Ingestion Stages & Planned Architecture

```
[Raw File Upload]
       │
       ▼
[Stage 1: Validation & Deduplication] ─── (SHA-256 Hash Check)
       │
       ▼
[Stage 2: Format-Specific Extraction] ─── (PyMuPDF for PDF, python-docx for DOCX)
       │
       ├── Has selectable text? ────────► [Text Stream Cleaned]
       └── Scanned / Empty?    ────────► [Tesseract OCR Applied]
       │
       ▼
[Stage 3: Structure-Aware Recursive Chunking] ─── (1000 char size, 200 overlap)
       │
       ▼
[Stage 4: Metadata Tagging] ─── (doc_id, page_no, chunk_id, file_hash)
       │
       ▼
[Stage 5: Batch Embedding Generation] ─── (Hugging Face BAAI/bge-small-en-v1.5, 384-dim)
       │
       ▼
[Stage 6: Qdrant Vector & Payload Indexing] ─── (HNSW Upsert)
       │
       ▼
[Stage 7: Ingestion Status Confirmation] ─── (Status updated to COMPLETED)
```

---

## 3. Detailed Stage Specifications

### Stage 1: Validation, Hashing & Storage
- **File Types**: Validated strictly against MIME types:
  - `application/pdf` (`.pdf`)
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (`.docx`)
- **Deduplication & Idempotency**:
  - The pipeline calculates a SHA-256 checksum of the raw bytes.
  - If a document with the identical hash already exists in Qdrant with status `COMPLETED`, the pipeline skips redundant re-indexing and returns the existing document ID.
- **Storage**: Binary saved using the `BaseDocumentStorage` abstraction.

### Stage 2: Format Extraction & Selective OCR
- **PDF Extraction (PyMuPDF)**:
  - Extract text page-by-page to maintain 1:1 page correlation.
  - If a page yields fewer than 50 characters of non-whitespace text, it is categorized as scanned or image-based.
- **Selective OCR (Tesseract via PyTesseract)**:
  - Scanned pages are rendered to an image buffer at 300 DPI.
  - Tesseract OCR processes the image, extracting recognized text while logging that OCR was applied for that specific page.
- **DOCX Extraction (python-docx)**:
  - Traverses paragraph elements and table rows, preserving structural heading levels (`Heading 1`, `Heading 2`, `Normal`).

### Stage 3: Structure-Aware Recursive Chunking
- Splitting purely by character count breaks sentences and destroys contextual cohesion.
- The recursive splitter uses prioritized separators:
  1. Major Section breaks (`\n\n## `, `\n\n# `)
  2. Paragraph breaks (`\n\n`)
  3. Sentence boundaries (`. `, `? `, `! `)
  4. Clause boundaries (`; `, `, `)
  5. Fallback space (` `)
- **Configurable Parameters**:
  - `CHUNK_SIZE`: Default 1000 characters (configurable via env).
  - `CHUNK_OVERLAP`: Default 200 characters (configurable via env).

### Stage 4: Metadata Preservation
Every chunk generated must adhere to this payload contract:
```json
{
  "chunk_id": "doc_8f1a2c_p3_c1",
  "document_id": "doc_8f1a2c",
  "document_name": "Academic_Handbook_2025.pdf",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "page_number": 3,
  "chunk_index": 1,
  "total_pages": 42,
  "char_count": 874,
  "ocr_applied": false,
  "text": "Extracted text content for this specific chunk..."
}
```

### Stage 5: Batch Embedding Generation
- Text is sent in batches (default batch size: 32 chunks) to the hosted Hugging Face Inference Providers using `BAAI/bge-small-en-v1.5`.
- Generates 384-dimensional normalized dense vectors.
- Includes exponential backoff retry logic for transient API rate limits (HTTP 429) and cold starts (HTTP 503).

### Stage 6: Vector Indexing (Qdrant Cloud)
- Vectors (384 dimensions) are upserted into Qdrant Cloud.
- Vectors use Cosine distance metric.
- Payloads are indexed for filtered retrieval (e.g., keyword index on `document_id`).

### Stage 7: Ingestion Lifecycle & Error Handling
Document status follows this state machine:
```
UPLOADED ──► PROCESSING ──► INDEXED
                 │
                 └── (on error) ──► FAILED
```
- If an error occurs midway through embedding or indexing:
  1. The transaction cleans up any partially inserted vectors in Qdrant for that `document_id`.
  2. The document record is marked `FAILED` with an error message.
  3. Partially processed documents are never presented as searchable.

---

## 4. Implementation Status Matrix

| Component | Planned Functionality | Current Implementation Status |
|---|---|---|
| PDF Text Extractor | PyMuPDF page-by-page extraction | ⏳ Not Started (Milestone 4) |
| DOCX Text Extractor | python-docx paragraph/table parsing | ⏳ Not Started (Milestone 4) |
| Selective OCR | Tesseract 300 DPI fallback | ⏳ Not Started (Milestone 4) |
| Recursive Chunking | Structure-aware recursive splitting | ⏳ Not Started (Milestone 4) |
| Hosted Embeddings | Hugging Face BAAI/bge-small-en-v1.5 (384 dim) | 🟢 Implemented (Milestone 2) |
| Qdrant Upsert & Search | Vector and payload indexing with payload index | 🟢 Implemented (Milestone 2) |
| Ingestion Pipeline Orchestrator | Pipeline coordinating extraction to Qdrant | ⏳ Not Started (Milestone 4 & 5) |
| Idempotency & Cleanup | Hash check and rollback on failure | ⏳ Not Started (Milestone 5) |

