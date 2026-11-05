# Data Flow & Execution Workflows

This document details the exact sequence of operations for the two primary lifecycle events in `RAG-Based-College-Knowledge-Assistant`:
1. **Document Ingestion Workflow**
2. **User Query & Retrieval Workflow**

---

## 1. Document Ingestion Workflow

The ingestion pipeline transforms unstructured college documents (PDF, DOCX) into semantically indexed, searchable chunks in Qdrant Cloud.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as College Administrator
    participant AdminApp as Admin Frontend (Vite)
    participant API as FastAPI Ingestion Endpoint
    participant Guard as Admin Secret Guard
    participant Storage as Storage Abstraction
    participant Pipeline as Ingestion Service
    participant Extractor as PyMuPDF / docx / OCR
    participant GeminiAPI as Gemini Embedding API
    participant Qdrant as Qdrant Cloud

    Admin->>AdminApp: Upload Document (PDF/DOCX)
    AdminApp->>API: POST /api/v1/documents/upload (Multipart + Admin Secret)
    API->>Guard: Verify ADMIN_API_SECRET
    alt Secret Invalid
        Guard-->>API: 401 Unauthorized
        API-->>AdminApp: Display Error
    else Secret Valid
        Guard-->>API: Authorized
        API->>Storage: Store raw file artifact
        Storage-->>API: file_storage_path / id
        API->>Pipeline: Schedule Ingestion Task (file_id)
        API-->>AdminApp: 202 Accepted (job_id, status="PROCESSING")

        Pipeline->>Extractor: Extract text page-by-page
        alt Page is scanned image / empty text
            Extractor->>Extractor: Invoke Tesseract OCR
        end
        Extractor-->>Pipeline: Extracted text with page numbers

        Pipeline->>Pipeline: Clean text & structure-aware recursive chunking
        Pipeline->>GeminiAPI: Generate embeddings (batch size <= 64)
        GeminiAPI-->>Pipeline: 768-dim embedding vectors

        Pipeline->>Qdrant: Upsert vectors with chunk payload metadata
        Qdrant-->>Pipeline: Index confirmed
        Pipeline->>Pipeline: Update job status to "COMPLETED"
    end
```

### Ingestion Step Details:
1. **Upload & Verification**: The administrator submits a PDF or DOCX file via the Admin Panel. The backend verifies the administrative token (`X-Admin-Secret`).
2. **Raw Storage & Hashing**: A SHA-256 hash of the file is calculated to verify idempotency. The raw binary is saved via the `BaseDocumentStorage` abstraction.
3. **Extraction & Selective OCR**:
   - For PDFs, PyMuPDF reads text streams page by page.
   - If a page has fewer than a configurable threshold of characters (e.g. < 50 chars), it is flagged as scanned and passed to Tesseract OCR.
   - For DOCX files, `python-docx` parses paragraphs, heading levels, and tables.
4. **Recursive Structure-Aware Chunking**: Text is split into chunks of ~1000 characters with 200-character overlap, respecting section headings, paragraph breaks, and sentence terminators.
5. **Metadata Tagging**: Each chunk is tagged with:
   - `document_id`: Unique document identifier
   - `document_name`: Filename (e.g. `Academic_Regulations_2025.pdf`)
   - `page_number`: 1-based page index
   - `chunk_index`: Sequence position
   - `chunk_id`: Unique deterministic chunk ID (`{doc_id}_{page}_{index}`)
   - `text`: Chunk text
6. **Batch Embedding**: Batches of chunk texts are sent to the Google Gemini `text-embedding-004` endpoint.
7. **Vector Indexing**: Chunks and their vectors are upserted into Qdrant Cloud under the configured collection name.

---

## 2. User Query & Retrieval Workflow

The query workflow accepts a student question, performs hybrid retrieval, merges candidate passages, and prompts the Gemini LLM to generate an answer grounded in cited documents.

```mermaid
sequenceDiagram
    autonumber
    actor Student as College Student
    participant UserApp as User Chatbot UI
    participant API as FastAPI Chat Endpoint
    participant Retrieval as Hybrid Retrieval Service
    participant GeminiAPI as Gemini API (Embed & Gen)
    participant Qdrant as Qdrant Cloud

    Student->>UserApp: Enter Question ("What is the attendance policy for semester exams?")
    UserApp->>API: POST /api/v1/chat/query { "question": "..." }

    API->>Retrieval: retrieve_context(query)
    
    par Dense Vector Search
        Retrieval->>GeminiAPI: Embed question (text-embedding-004)
        GeminiAPI-->>Retrieval: query_vector
        Retrieval->>Qdrant: Query top-K vectors (cosine similarity)
        Qdrant-->>Retrieval: Dense candidate list [R_dense]
    and Sparse / Keyword Search
        Retrieval->>Retrieval: Search keyword index / Qdrant text match
        Retrieval-->>Retrieval: Keyword candidate list [R_keyword]
    end

    Retrieval->>Retrieval: Merge candidates via Reciprocal Rank Fusion (RRF)
    Retrieval-->>API: Top ranked context chunks with metadata

    alt No relevant context found (similarity below threshold)
        API->>UserApp: "I cannot find authoritative information in the official documents."
    else Sufficient context retrieved
        API->>GeminiAPI: Prompt gemini-2.5-flash with Grounded System Instruction + Context
        GeminiAPI-->>API: Grounded answer with explicit citation references
        API-->>UserApp: 200 OK { answer, sources: [{ doc, page, snippet }] }
        UserApp-->>Student: Render answer & clickable citation cards
    end
```

### Query Step Details:
1. **Query Validation**: Chat endpoint validates the query length and schema.
2. **Parallel Hybrid Retrieval**:
   - **Dense Search**: Converts the user's natural query into a 768-dimensional vector and executes an approximate nearest-neighbor query in Qdrant.
   - **Keyword Search**: Performs exact and stemmed keyword matching against document text payloads to capture exact course numbers, dates, or faculty codes.
3. **Reciprocal Rank Fusion (RRF)**:
   - Rank scores are calculated using the standard formula:
     $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{dense}, \text{keyword}\}} \frac{1}{k + \text{rank}_m(d)}$$
     *(with constant $k = 60$)*
   - Chunks are re-ordered by combined RRF score, producing a deduplicated, high-precision context pool.
4. **Context Construction & Prompting**:
   - The top candidate chunks are assembled into a structured prompt with explicit document boundaries and page identifiers.
   - The system prompt forbids speculation, requires citing exact sources, and directs the model to state if the answer cannot be found in the provided excerpts.
5. **Answer Delivery**:
   - The response is returned to the user frontend along with structured source metadata for transparent verification.

