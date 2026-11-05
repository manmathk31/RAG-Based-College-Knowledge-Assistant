# RAG-Based-College-Knowledge-Assistant

[![Architecture: Modular Monolith](https://img.shields.io/badge/Architecture-Modular%20Monolith-blue)](docs/architecture/SYSTEM_ARCHITECTURE.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Frontend: React + Vite](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20TS-61DAFB)](https://vitejs.dev/)
[![Vector DB: Qdrant Cloud](https://img.shields.io/badge/Vector%20DB-Qdrant%20Cloud-DC2626)](https://qdrant.tech/)
[![LLM: Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-8E75B2)](https://ai.google.dev/)

An engineering-grade, maintainable College Knowledge Assistant powered by Retrieval-Augmented Generation (RAG). Students can query academic policies, admission guidelines, fee structures, and campus services via a responsive chatbot that generates grounded answers backed by precise document and page citations. Administrators manage and monitor the document ingestion lifecycle through an isolated administrative interface.

---

## Repository Structure

```text
RAG-Based-College-Knowledge-Assistant/
├── AGENTS.md                  # Persistent AI and engineering instructions
├── README.md                  # Main project overview & quickstart
├── .gitignore                 # Root gitignore rules
├── .env.example               # Root environment configuration template
├── docker-compose.yml         # Optional local containerization
│
├── docs/                      # Comprehensive engineering documentation
│   ├── architecture/          # System architecture, data flows, ingestion pipeline
│   ├── decisions/             # Architecture Decision Records (ADRs)
│   ├── development/           # Setup guide, coding standards, testing policy
│   └── project/               # Project status, implementation roadmap, changelog
│
├── frontend/                  # Dual independent frontend applications
│   ├── user-app/              # Student-facing chatbot (React, TS, Vite, Tailwind)
│   └── admin-app/             # Admin document management portal (React, TS, Vite, Tailwind)
│
├── backend/                   # Modular FastAPI backend
│   ├── app/
│   │   ├── api/               # API route controllers (v1/health, v1/chat, v1/documents)
│   │   ├── core/              # Configuration (Pydantic Settings), logging, exceptions
│   │   ├── db/                # Supabase PostgreSQL session, models, Alembic migrations
│   │   ├── schemas/           # Pydantic request/response contracts
│   │   ├── ingestion/         # PDF/DOCX extractors, OCR, token chunking, orchestrator
│   │   ├── retrieval/         # Dense + keyword hybrid search, RRF fusion, context builder
│   │   ├── generation/        # Gemini grounded answer synthesis with citations
│   │   ├── vector_store/      # Qdrant Cloud vector-store adapter
│   │   ├── embeddings/        # Hosted Hugging Face embedding service
│   │   ├── storage/           # Storage abstraction layer
│   │   └── main.py            # FastAPI application entry point
│   ├── tests/                 # Targeted Pytest suite (96 tests passing)
│   ├── requirements.txt       # Python dependencies
│   └── pyproject.toml         # Python project configuration
│
└── scripts/                   # Development and maintenance utilities
```

---

## Quickstart & Local Development

### 1. Prerequisites
- Python 3.11+ (virtual environment `venv` pre-configured)
- Node.js 20+ & npm 10+
- Qdrant Cloud cluster & Google Gemini API key

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and QDRANT credentials
```

### 3. Start Backend
```powershell
cd backend
..\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```
- API Health Check: `http://localhost:8000/api/v1/health`
- Swagger UI Documentation: `http://localhost:8000/docs`

### 4. Start Frontends
```powershell
# In terminal 2: User Chatbot
cd frontend/user-app
npm install
npm run dev

# In terminal 3: Admin Panel
cd frontend/admin-app
npm install
npm run dev -- --port 5174
```

---

## Core Engineering Documentation

- [Frontend API Integration Guide](docs/frontend/API_INTEGRATION_GUIDE.md): Complete API handoff guide, schemas, citations, and frontend code examples.
- [AGENTS.md](AGENTS.md): Architectural invariants, coding rules, and testing policy for developers and AI agents.
- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md): Component breakdown and high-level Mermaid architecture diagrams.
- [Data Flow & Sequence](docs/architecture/DATA_FLOW.md): Step-by-step ingestion and query workflows.
- [Ingestion Pipeline Specification](docs/architecture/INGESTION_PIPELINE.md): PDF/DOCX parsing, selective OCR, and chunking strategy.
- [Architecture Decision Records (ADR-001)](docs/decisions/ADR-001-INITIAL-ARCHITECTURE.md): 10 foundational technical choices.
- [Development Guide](docs/development/DEVELOPMENT_GUIDE.md): Local environment setup, running commands, and debugging.
- [Testing Strategy](docs/development/TESTING_STRATEGY.md): The 10 rules of testing, test structure, and commands.
- [Implementation Plan](docs/project/IMPLEMENTATION_PLAN.md): 12 development milestones and dependencies.
- [Project Status](docs/project/PROJECT_STATUS.md): Current implementation progress dashboard.
