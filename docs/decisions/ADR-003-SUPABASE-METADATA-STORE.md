# ADR-003: Supabase PostgreSQL for Authoritative Document Metadata & Ingestion Lifecycle

## Status
**ACCEPTED** (2026-11-05)

## Context & Problem Statement
In Milestone 1 and 2, document metadata was initially planned to reside solely within Qdrant payloads to avoid unnecessary database complexity. However, as the end-to-end ingestion pipeline and administrative requirements took shape, several concrete requirements emerged that pure vector store payloads cannot reliably satisfy:

1. **Document Identity & Versioning**: Administrators upload new revisions of documents (e.g. `Academic_Calendar_2025.pdf`). The system must enforce composite uniqueness on `(normalized_filename, document_version)`, track historical versions, and swap active versions atomically.
2. **Authoritative Ingestion Lifecycle**: Document processing transitions through states (`queued → processing → completed / failed`). An administrative panel requires tracking processing timestamps, failure diagnostics, and deduplication hashes independently of vector indexing.
3. **Auditability & Pagination**: Standard administrative operations require paginated listing, status filtering, and total record counts without executing expensive full-collection scroll queries across vector embeddings.
4. **Resilience During Retries & Rollbacks**: If vector indexing fails midway, compensating cleanup must be tracked against an authoritative state machine to prevent orphan vectors or ambiguous document states.

## Decision
We adopt **Supabase PostgreSQL** as our dedicated relational metadata database, establishing an architecture with **exactly two persistent data stores**:

1. **Supabase PostgreSQL**:
   - Authoritative document registry.
   - Document metadata (`original_filename`, `normalized_filename`, `file_type`, `file_size`, `content_hash`).
   - Monotonic versioning and active version flags (`document_version`, `is_active`).
   - Ingestion lifecycle state machine (`status`, timestamps, `error_message`).
   - Implemented using SQLAlchemy 2.x with asynchronous `asyncpg` driver and Alembic migrations.

2. **Qdrant Cloud**:
   - Vector storage for dense chunk embeddings (384-dimensional `BAAI/bge-small-en-v1.5`).
   - Retrieval payloads (`chunk_id`, `document_id`, `document_version`, `page_number`, `section`, `content`).
   - In-memory / payload keyword filtering.

3. **Ephemeral Original File Storage**:
   - Uploaded PDF and DOCX documents are processed strictly via temporary disk files with guaranteed cleanup in `try...finally` blocks.
   - We do NOT store original binaries permanently in S3, Supabase Storage, or local disk. Reprocessing requires re-uploading the original file.

4. **Consistency & Compensating Cleanup Strategy**:
   - Because Supabase PostgreSQL and Qdrant Cloud do not share an atomic two-phase commit (2PC) distributed transaction, consistency is managed via explicit compensating workflows:
     - On ingestion failure: Partially indexed points in Qdrant are deleted via `delete_by_document_id`, and the Supabase record is marked `failed`.
     - On version replacement: New version chunks are fully indexed and activated in Supabase (`is_active=True`) before old version vectors are purged from Qdrant.
     - On document deletion: Associated vectors are purged from Qdrant prior to removing the metadata records from Supabase.
   - Search queries filter on `is_active=True`, preventing stale or failed versions from appearing in retrieval results.

## Consequences & Trade-offs
### Positive
- Strict relational constraints and composite uniqueness prevent race conditions during versioning.
- Fast, standard SQL pagination and status filtering for admin views.
- Vector search remains fast and fully decoupled; retrieval does NOT need to query PostgreSQL on every user question.
- Clean administrative API with explicit 401 (Unauthorized), 404 (Not Found), 415 (Unsupported Media), and 503 (Database Unavailable) error handling.

### Negative / Trade-offs
- Requires managing PostgreSQL connection pooling (`pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`).
- Cross-database updates require explicit compensating code paths rather than native ACID transactions.
- Offline documents cannot be re-extracted without the user re-uploading the original file.

