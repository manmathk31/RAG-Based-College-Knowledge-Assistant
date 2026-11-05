# System Architecture

## 1. High-Level Overview

`RAG-Based-College-Knowledge-Assistant` is a Retrieval-Augmented Generation (RAG) platform tailored for higher education institutions. The system enables students to query college policies, academic calendars, syllabi, fee structures, and campus procedures, delivering answers strictly grounded in official documents with verifiable citations.

The architecture emphasizes modularity, zero vendor lock-in where feasible, persistent cloud vector storage without local disk dependencies, and low maintenance overhead.

```mermaid
flowchart TD
    subgraph Frontends ["Client Tier (React + TypeScript + Vite)"]
        UserApp["Student Chatbot UI<br/>(Port 5173 / Mobile-first)"]
        AdminApp["Admin Management UI<br/>(Port 5174 / Desktop)"]
    end

    subgraph BackendGateway ["API Gateway & Core (FastAPI Monolith)"]
        CORS["CORS & Request Validation"]
        AuthMiddleware["Admin Secret Guard"]
        RouterChat["/api/v1/chat"]
        RouterIngest["/api/v1/documents"]
        RouterHealth["/api/v1/health"]
    end

    subgraph BackendServices ["Application Services Tier"]
        IngestionSvc["Ingestion Pipeline Service<br/>(PyMuPDF / docx / Tesseract OCR)"]
        RetrievalSvc["Hybrid Retrieval Service<br/>(Dense Vectors + Keyword Search + RRF)"]
        GenerationSvc["Generation Service<br/>(Grounded Prompting + Source Attribution)"]
        StorageSvc["Storage Abstraction Layer<br/>(File Storage Interface)"]
    end

    subgraph ExternalServices ["External Cloud Services Tier"]
        HFEmbed["Hugging Face Inference Providers<br/>(BAAI/bge-small-en-v1.5, 384-dim)"]
        GeminiGen["Google Gemini API<br/>(gemini-2.5-flash - Planned M7)"]
        QdrantCloud[("Qdrant Cloud<br/>(Persistent Vectors & Payloads)")]
    end

    UserApp -->|POST /chat/query| CORS
    AdminApp -->|POST /documents/upload| CORS
    CORS --> AuthMiddleware
    AuthMiddleware --> RouterIngest
    CORS --> RouterChat
    CORS --> RouterHealth

    RouterChat --> RetrievalSvc
    RouterChat --> GenerationSvc
    RouterIngest --> IngestionSvc

    IngestionSvc --> StorageSvc
    IngestionSvc --> HFEmbed
    HFEmbed --> IngestionSvc
    IngestionSvc --> QdrantCloud

    RetrievalSvc --> HFEmbed
    RetrievalSvc --> QdrantCloud
    GenerationSvc --> GeminiGen
```

---

## 2. Component Breakdown

### 2.1 User Frontend (`frontend/user-app`)
- **Technology**: React 18/19, TypeScript, Vite, Tailwind CSS.
- **Role**: Responsive, mobile-first conversational chat interface for students.
- **Key Responsibilities**:
  - Accept natural-language queries.
  - Display AI responses with distinct, expandable source citation cards (document name, page number, matching snippet).
  - Provide clear loading states, network error handling, and session conversation display.
  - Communicate with backend using typed HTTP services (`services/api.ts`).

### 2.2 Admin Frontend (`frontend/admin-app`)
- **Technology**: React 18/19, TypeScript, Vite, Tailwind CSS.
- **Role**: Clean administrative workspace for document management.
- **Key Responsibilities**:
  - Drag-and-drop file upload for PDF and DOCX files.
  - Document status dashboard (uploaded, processing, indexed, failed).
  - Ingestion progress tracking and error log inspection.
  - Document deletion or re-indexing management.

### 2.3 Backend Modular Monolith (`backend/app`)
- **Technology**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2.
- **Role**: Central coordinator for document processing, retrieval, and generation.
- **Modules**:
  - `core`: Centralized environment configuration (`pydantic-settings`), custom logging, error handlers.
  - `api`: Versioned route controllers (`/api/v1/health`, `/api/v1/documents`, `/api/v1/chat`).
  - `schemas`: Strict Pydantic models for request validation and response contracts.
  - `ingestion`: File parsing, text extraction, selective OCR, structure-aware chunking.
  - `retrieval`: Dense vector querying, keyword candidate matching, Reciprocal Rank Fusion (RRF).
  - `generation`: Context synthesis, prompt building with strict grounding constraints, citation formatting.
  - `vector_store`: Interface and client for Qdrant Cloud.
  - `storage`: Pluggable storage abstraction for raw document persistence without local disk coupling.

### 2.4 Vector Storage Tier (`Qdrant Cloud`)
- **Role**: Managed vector database.
- **Storage Strategy**:
  - Vectors generated from text via `BAAI/bge-small-en-v1.5` (384 dimensions) using Cosine distance.
  - Rich payloads containing `document_id`, `document_name`, `document_version`, `page_number`, `section`, `chunk_id`, `chunk_index`, `content`, `content_hash`, and `embedding_model`.
  - HNSW indexing enabled for real-time nearest neighbor similarity search.
  - Payload index created on `document_id` for fast filtered document deletions and scoped queries.

### 2.5 Hosted Embeddings (`Hugging Face Inference Providers`)
- **Model**: `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors, task: `feature-extraction`).
- **Client**: Official `huggingface_hub.AsyncInferenceClient`.
- **Batching & Retries**: Automatic sub-batch chunking (`EMBEDDING_BATCH_SIZE=32`), bounded exponential backoff on HTTP 429 and 503, strict dimension validation.
- **Free-Tier Limits & Operational Notes**:
  - Hugging Face serverless free-tier inference is subject to rate limits and occasional cold starts (HTTP 503 while models load on shared servers).
  - The adapter gracefully handles cold starts with backoff retries.
  - The service is not permanently unlimited; dedicated Inference Endpoints or Pro subscriptions are recommended for high-volume production deployments.

### 2.6 External LLM Tier (`Google Gemini API` - Planned Milestone 7)
- **Answer Generation**: `gemini-2.5-flash` for fast, cost-effective generation adhering to strict context-grounding prompts. (Not implemented in Milestone 2).

---

## 3. Storage Abstraction Layer

The backend is explicitly designed to avoid hard dependencies on local disk persistence:
- An abstract class `BaseDocumentStorage` defines operations: `save_document`, `get_document`, `delete_document`, and `exists`.
- **Development implementation**: Ephemeral local or memory buffer storage.
- **Production implementation**: Cloud blob storage (e.g. AWS S3, Cloudflare R2, Google Cloud Storage, or Supabase Storage) easily plugged in by configuring an environment variable without modifying business logic.

---

## 4. Operational Invariants & Concurrency

- **Target Capacity**: ~10 concurrent active users.
- **Concurrency Model**: Native Python asynchronous I/O (`async`/`await`) for HTTP requests to external APIs (Gemini, Qdrant).
- **CPU-Intensive Tasks**: PDF parsing, OCR image processing, and chunking run in thread executors to keep the asyncio event loop responsive.
- **Stateless Application**: Backend instances carry no in-memory state that prevents multiple instances from operating concurrently.

