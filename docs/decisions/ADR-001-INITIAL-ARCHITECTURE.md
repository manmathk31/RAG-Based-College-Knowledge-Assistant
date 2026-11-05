# ADR-001: Initial Architecture & Technology Stack

- **Status**: ACCEPTED
- **Date**: 2026-11-05
- **Deciders**: Software Architect & Engineering Lead, Project Contributors

---

## 1. Context & Problem Statement

The goal of the `RAG-Based-College-Knowledge-Assistant` project is to deliver an accurate, grounded, and maintainable college knowledge retrieval system for college students and administrators. Students must be able to ask natural-language questions and receive answers cited from official documents. Administrators need an interface to upload and manage college documents (PDF, DOCX) and monitor ingestion status.

As a third-year BTech engineering project aiming for industry-grade standards without unnecessary complexity, we must establish clear architectural guardrails before writing feature code. We must make deliberate choices regarding repository structure, frontend architecture, backend organization, vector storage, model hosting, authentication, persistence, retrieval strategy, deployment targets, and operational scope.

---

## 2. Decision Log of Core Architectural Choices

### Decision 1: Monorepo Structure
- **Decision**: Organize the project as a single monorepo containing `docs/`, `backend/`, `frontend/user-app/`, `frontend/admin-app/`, and `scripts/`.
- **Reasoning**: A single repository provides atomic versioning, simplified cross-layer documentation, easy environment reproduction, and synchronized commits without the overhead of polyrepo dependency synchronization.
- **Trade-offs**: Requires disciplined directory boundaries so frontend and backend dependencies do not bleed into each other.
- **Consequences**: Independent dependency manifests (`requirements.txt` for backend, `package.json` for each frontend) will be maintained. No complex monorepo workspace tooling (Turborepo/Lerna) is needed.

### Decision 2: Two Separate React Applications
- **Decision**: Build two independent React + TypeScript + Vite applications (`frontend/user-app` for students, `frontend/admin-app` for administrators).
- **Reasoning**: The user experience, design goals, and operational risks of a student-facing chatbot differ drastically from an administrative document-management dashboard. Isolating them prevents bundle bloat, prevents accidental administrative code leaking into the public bundle, and allows independent styling and deployment.
- **Trade-offs**: Minor duplication of shared UI utilities or CSS base styling.
- **Consequences**: Each frontend runs on its own local port (5173 for user-app, 5174 for admin-app) and builds to its own `dist/` bundle.

### Decision 3: FastAPI Modular Monolith
- **Decision**: Implement the backend as a modular monolith in FastAPI (Python).
- **Reasoning**: Microservices add distributed tracing, network latency, multiple deployment targets, and service mesh overhead, which are completely unjustified for a system with ~10 concurrent users. FastAPI provides high-speed asynchronous handling, automatic OpenAPI schema generation, and deep integration with Python's rich data and RAG ecosystem (PyMuPDF, python-docx, pytesseract).
- **Trade-offs**: Strict internal module boundaries must be enforced manually to prevent circular dependencies.
- **Consequences**: Business logic is cleanly separated into `core`, `api`, `ingestion`, `retrieval`, `generation`, `vector_store`, and `storage`.

### Decision 4: Qdrant Cloud as Vector Database
- **Decision**: Use Qdrant Cloud as the dedicated persistent vector database.
- **Reasoning**: Qdrant provides a generous free tier, persistent cloud hosting, high-performance HNSW vector indexing, rich payload filtering, and native Python SDK support. Unlike local SQLite-based vector extensions or ChromaDB, Qdrant Cloud persists vector data independently of the local backend filesystem, making serverless or ephemeral container deployments viable.
- **Trade-offs**: Requires external network connectivity and reliance on an external cloud vendor.
- **Consequences**: No other vector databases (Supabase pgvector, Pinecone, ChromaDB, Weaviate) will be introduced.

### Decision 5: Hosted Google Gemini APIs for Embeddings and Generation
- **Decision**: Use hosted Google Gemini APIs (`text-embedding-004` for vector embeddings and `gemini-2.5-flash` for answer generation).
- **Reasoning**: Hosting local 7B+ LLMs or embedding models locally requires heavy GPU hardware and substantial RAM, which is impractical for free-tier cloud deployment or typical developer laptops. Gemini offers state-of-the-art reasoning, low latency, generous free/low-cost tiers, and large context windows.
- **Trade-offs**: Dependent on Gemini API rate limits and network latency.
- **Consequences**: Provider integrations are hidden behind clean service interfaces to allow mocking during unit testing.

### Decision 6: Authentication Scope in Initial Version
- **Decision**: Exclude full user registration, login, JWT token management, and multi-tenant user accounts from the initial scope. For the admin upload routes, implement lightweight protection using an environment-configured secret header (`ADMIN_API_SECRET`).
- **Reasoning**: The core technical objective is RAG accuracy, robust extraction, OCR, hybrid search, and source attribution. A full identity provider or auth system would consume excessive development time without adding value to the core RAG problem.
- **Trade-offs**: No user-specific chat history persistence or per-user permission tiers initially.
- **Consequences**: Backend routes verify the admin token header for sensitive operations. Chat endpoints remain open for public college queries.

### Decision 7: Single-Database Philosophy (No Second Database Initially)
- **Decision**: Avoid introducing a relational database (PostgreSQL, MySQL, SQLite) or document store (MongoDB) alongside Qdrant initially. Document metadata, ingestion status, chunk boundaries, and source references will be stored directly inside Qdrant payloads.
- **Reasoning**: Qdrant supports complex metadata filtering and payload storage alongside vectors. Introducing PostgreSQL or MongoDB adds unnecessary migration tooling, ORMs, connection pooling, and multi-service synchronization overhead for ~10 users.
- **Trade-offs**: Querying purely relational aggregations or complex transaction joins across documents requires querying Qdrant payload filters.
- **Consequences**: If future requirements (such as multi-user chat session history or complex relational audit trails) genuinely demand a relational database, an ADR will be drafted to evaluate a minimal SQLite/PostgreSQL addition before implementation.

### Decision 8: Hybrid RAG Retrieval Strategy
- **Decision**: Implement hybrid retrieval combining dense vector similarity search (Gemini embeddings via Qdrant) with lightweight keyword retrieval, combined using Reciprocal Rank Fusion (RRF).
- **Reasoning**: Dense semantic retrieval excels at conceptual questions ("How can I apply for financial aid?"), but often struggles with exact college acronyms, course codes, course numbers, or specific faculty names (e.g., "CS-301 syllabus", "Dean Dr. R. K. Sharma"). Keyword retrieval resolves exact matches, and RRF seamlessly merges dense and sparse rankings without requiring score normalization calibration.
- **Trade-offs**: Requires running both vector query and keyword matching on user queries.
- **Consequences**: Keyword retrieval will be implemented using a lightweight, PostgreSQL-independent approach (e.g., Qdrant payload text matching or in-memory BM25 index over retrieved candidate chunks).

### Decision 9: Free-Tier-First Deployment Strategy
- **Decision**: Design the application to deploy seamlessly on free-tier platforms (e.g., Render / Railway / Fly.io for backend, Vercel / Netlify for frontends, Qdrant Cloud for vector data).
- **Reasoning**: The project must remain zero-cost and accessible for demonstration, grading, and testing without requiring paid cloud infrastructure or persistent VPS disks.
- **Trade-offs**: Free-tier backend compute may have cold starts or ephemeral local disk storage.
- **Consequences**: The backend must never rely on local filesystem writes for persistent state. Document storage must use an abstract storage interface that can support cloud blob storage (or in-memory temporary processing).

### Decision 10: Scope Limitations & Simplicity Invariants
- **Decision**: Explicitly prohibit agentic loops (LangGraph/AutoGPT loops), autonomous tool-calling agents, Celery/Redis queues, microservices, and Kubernetes orchestration in this project.
- **Reasoning**: For an expected load of ~10 concurrent users, simple asynchronous Python coroutines, standard FastAPI background tasks, and clean direct API calls are robust, easy to debug, and fast to test. Over-engineering with message brokers and distributed agents introduces failure modes without measurable performance benefits.
- **Trade-offs**: Ingestion runs within FastAPI background tasks or bounded threadpools rather than distributed worker fleets.
- **Consequences**: Maintainable, comprehensible codebase that third-year students can thoroughly explain and defend during evaluation.

