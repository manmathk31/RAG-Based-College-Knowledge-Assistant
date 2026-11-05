# AGENTS.md — Persistent Engineering & Operating Instructions

> **Notice to AI Coding Agents**: This document is the single source of truth for architectural invariants, engineering conventions, RAG design principles, and operational rules in this repository. You MUST read this document thoroughly before inspecting, planning, or modifying any code in this project.

---

## 1. Project Identity & Purpose

`RAG-Based-College-Knowledge-Assistant` is a maintainable, production-ready college knowledge assistant built using Retrieval-Augmented Generation (RAG).

### 1.1 Core Purpose
College students frequently struggle to find authoritative information regarding syllabi, admission guidelines, fee structures, examination schedules, grading policies, and campus services. This application provides:
1. A **User Chatbot Interface** where students ask natural-language questions and receive grounded, accurate answers accompanied by clear, verifiable source citations (document name, page, and section).
2. An **Admin Panel Interface** where college administrators upload official documents (PDF, DOCX) and monitor the ingestion, chunking, and vector indexing lifecycle.

### 1.2 Target Audience & Expected Concurrency
- **Audience**: College students, faculty, and administrative staff.
- **Expected Concurrency**: ~10 concurrent users. The system is designed for sensible asynchronous I/O, bounded concurrency, and defensive error handling, without over-engineering for massive hyperscale or distributed microservices.

---

## 2. Established Architectural Decisions

These technical decisions are locked. AI agents MUST NOT alter, replace, or work around these choices without explicit human authorization:

| Layer / Concern | Established Choice | Rationale & Boundaries |
|---|---|---|
| **Frontends** | React + TypeScript + Vite + Tailwind CSS | Two isolated frontend apps (`frontend/user-app` and `frontend/admin-app`). |
| **Backend** | FastAPI (Python) | Modular monolith with clean domain separation. No microservices. |
| **Vector Database** | Qdrant Cloud | Managed vector store for persistent vector storage and metadata filtering. No Supabase, ChromaDB, or Pinecone. |
| **Embedding Provider** | Hugging Face Inference Providers (`BAAI/bge-small-en-v1.5`, 384 dim) | Hosted feature-extraction API to avoid heavy local GPU dependencies. Configurable provider. |
| **LLM Provider** | Google Gemini API (`gemini-2.5-flash`) | Fast, cost-efficient, grounded answer generation. |
| **PDF Extraction** | PyMuPDF (`fitz`) | High-speed, robust PDF parsing. |
| **DOCX Extraction** | `python-docx` | Native XML-based Word document parsing. |
| **Selective OCR** | Tesseract OCR (`pytesseract`) | Invoked only for scanned PDF pages or pages with minimal selectable text. |
| **Keyword Retrieval** | In-memory / Qdrant payload text match | Lightweight hybrid retrieval without introducing an external search cluster. |
| **Relational Database** | None initially | Metadata stored directly in Qdrant payloads. Do not add Postgres/MySQL without documented justification. |
| **Authentication** | Lightweight Admin Secret | No student user accounts or auth flows initially. Admin endpoints protected via header secret. |

---

## 3. Engineering Rules & Quality Standards

All code written in this repository must comply with the following standards:

### 3.1 Architecture & Separation of Concerns
- **Modular Monolith**: Keep domain logic inside dedicated modules under `backend/app/` (`core`, `api`, `ingestion`, `retrieval`, `generation`, `vector_store`, `storage`, `schemas`).
- **No Logic in Routes**: FastAPI route handlers (`app/api/`) must only parse incoming requests, call domain services, and return validated schemas. Business rules, chunking, math, and external API calls belong in service modules.
- **Strict Interfaces**: External integrations (Qdrant, Gemini, Storage) must sit behind abstract base interfaces (`base.py`) to permit unit testing and mock injection.
- **No Shared Frontend Workspaces**: `user-app` and `admin-app` are independent applications with separate `package.json` files. Do not build custom NPM monorepo packages unless explicitly requested.

### 3.2 Data Validation & Schemas
- **Pydantic Everywhere**: Every API request and response payload must have an explicit Pydantic model (`app/schemas/`). Never use raw untyped dictionaries for API inputs or outputs.
- **TypeScript Strictness**: In frontend applications, use explicit interfaces and types for API responses, props, and state. Avoid `any` unless absolutely necessary for third-party untyped libraries.
- **Frontend API Separation**: UI components must not make direct `fetch` or `axios` calls. All API communication must reside in dedicated service files (e.g., `services/api.ts`).

### 3.3 Security & Secret Management
- **Zero Secret Leakage**: Never hardcode API keys, tokens, or credentials in any file. All secrets are read via `pydantic-settings` from environment variables.
- **Defensive Error Handling**: Catch and handle exceptions explicitly. Never return raw Python tracebacks, database connection strings, or system paths to frontend clients. Return structured error schemas.

---

## 4. RAG-Specific Principles & Invariants

When developing ingestion, retrieval, or generation features:

1. **Source Metadata Preservation**:
   - Every single chunk stored in Qdrant MUST contain: `document_id`, `document_name`, `page_number` (or section title), `chunk_id`, and `total_pages`.
   - Never strip or lose metadata during chunking or extraction.
2. **Selective OCR**:
   - Do not assume PDFs are clean digital text. Always check if a PDF page has sufficient selectable text; if not, invoke Tesseract OCR.
3. **Structure-Aware Chunking**:
   - Use recursive chunking that respects paragraph and heading boundaries. Avoid breaking sentences or words midway unless the chunk size limit requires it.
4. **Ingestion Idempotency & Lifecycle**:
   - Ingestion jobs must be idempotent. Re-uploading the same document version must safely replace or invalidate old chunks without leaving orphan vectors.
   - Do not mark a document as "indexed" until all chunks have been embedded and stored in Qdrant successfully.
5. **Separation of Retrieval and Generation**:
   - The retrieval pipeline (dense vector + keyword search + Reciprocal Rank Fusion) must be testable independently of LLM generation.
6. **Strict Source Grounding**:
   - The LLM generation prompt must strictly instruct the model to ground answers in the provided context.
   - If the retrieved context does not contain sufficient information, the model must explicitly state that the information is unavailable, rather than hallucinating or citing nonexistent documents.
   - Never fabricate citations.

---

## 5. Testing Policy & Efficiency Rules

We optimize for developer velocity and signal-to-noise ratio. Follow these rules:

1. **No Constant Re-Testing**: Do not run full test suites after every small code edit.
2. **Targeted Verification**: Use targeted tests or lint checks when a domain module is completed.
3. **Integration Milestones**: Run integration tests only when two or more distinct modules are connected.
4. **Honest Reporting**: Never claim tests passed unless they were actually executed and exited with code 0.
5. **No Blind Retries**: If a test fails, analyze the root cause before re-running. Never repeatedly rerun failing tests hoping for different results.
6. **High-Value Focus**: Prioritize tests for PDF extraction, chunking boundary logic, RRF fusion math, Qdrant payload serialization, and API contracts.

---

## 6. AI Coding Agent Protocol

As an AI coding agent operating in this repository, you must adhere to the following workflow:

1. **Pre-Flight Check**: Read `AGENTS.md` and check `docs/project/PROJECT_STATUS.md` before making any modifications.
2. **Scope Discipline**: Implement only the milestone or task requested. Do not preemptively implement future milestones or introduce unrequested third-party packages.
3. **No Unrelated Rewrites**: Do not reformat or rewrite files outside the scope of your assigned task.
4. **Documentation Updates**:
   - Update `docs/project/PROJECT_STATUS.md` when completing a milestone or encountering a blocker.
   - Record architectural changes or newly evaluated trade-offs in `docs/decisions/`.
   - Log notable milestones in `docs/project/CHANGELOG.md`.
5. **Preserve Environment Integrity**: Respect the user's existing virtual environment (`venv`). Do not create duplicate virtual environments.

