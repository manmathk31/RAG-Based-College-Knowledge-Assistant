# Development Guide

This guide covers local environment setup, configuration, and day-to-day development workflows for `RAG-Based-College-Knowledge-Assistant`.

---

## 1. Prerequisites

Ensure the following tools are installed on your machine:
- **Python**: 3.11+ (We use the pre-created `venv` environment in this workspace).
- **Node.js**: 20.x or 22+ LTS (`node --version`).
- **NPM**: 10.x+ (`npm --version`).
- **Git**: 2.x+
- **Tesseract OCR**: (Optional for baseline setup, required for OCR testing).
  - Windows: Install via [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract.exe` is in your `PATH`.
  - Linux/macOS: `sudo apt-get install tesseract-ocr` or `brew install tesseract`.

---

## 2. Repository & Virtual Environment Setup

### 2.1 Virtual Environment
The virtual environment `venv` is already established at the root of the project:
```powershell
# In PowerShell (Windows):
.\venv\Scripts\Activate.ps1

# Or in Git Bash / WSL:
source venv/Scripts/activate
```

> **Note**: Do not recreate or commit the `venv` directory. It is ignored by Git.

### 2.2 Backend Dependencies
With the virtual environment activated, install the backend requirements:
```powershell
cd backend
pip install -r requirements.txt
```

### 2.3 Frontend Dependencies
Install dependencies for both frontend applications:
```powershell
# Install User App dependencies
cd ../frontend/user-app
npm install

# Install Admin App dependencies
cd ../admin-app
npm install
```

---

## 3. Environment Variable Configuration

Copy the example configuration to a local `.env` file in the project root:
```powershell
# From project root
Copy-Item .env.example .env
```

### Required Configuration Values:
1. **Supabase PostgreSQL (Authoritative Metadata Database)**:
   - Create a project on [Supabase](https://supabase.com/).
   - Obtain your PostgreSQL connection string from Database Settings.
   - Set `DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres` (or transaction pooler on port 6543).
   - Apply schema migrations: `alembic upgrade head`.
2. **Hugging Face Inference Providers (Embeddings)**:
   - Create a free account on [Hugging Face](https://huggingface.co/).
   - Generate an Access Token (Read permissions) under [Settings > Access Tokens](https://huggingface.co/settings/tokens).
   - Set `HF_TOKEN=hf_your_token_here`.
   - Default model: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5` (dimension: `384`).
3. **Qdrant Cloud (Vector Database)**:
   - Create a free cluster on [Qdrant Cloud Console](https://cloud.qdrant.io/).
   - Obtain your cluster URL and API key.
   - Set `QDRANT_URL=https://<cluster-id>.<region>.gcp.cloud.qdrant.io:6333`.
   - Set `QDRANT_API_KEY=your_qdrant_key`.
   - Set `QDRANT_COLLECTION_NAME=college_knowledge_base`.
4. **Google Gemini API (Answer Generation - Planned Milestone 7)**:
   - Obtain a key from [Google AI Studio](https://aistudio.google.com/).
   - Set `GEMINI_API_KEY=your_actual_key`.
5. **Admin Protection**:
   - Set `ADMIN_API_SECRET=your_custom_admin_token` (used in request headers to protect administrative uploads).

---

## 4. Running the Applications Locally

Open separate terminal windows for each process:

### 4.1 Running the Backend (FastAPI)
```powershell
# Terminal 1: Backend
cd backend
..\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```
- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs (Swagger): `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

### 4.2 Running the Student Chatbot Frontend
```powershell
# Terminal 2: User Frontend
cd frontend/user-app
npm run dev
```
- Student Chatbot URL: `http://localhost:5173`

### 4.3 Running the Admin Panel Frontend
```powershell
# Terminal 3: Admin Frontend
cd frontend/admin-app
npm run dev -- --port 5174
```
- Admin Panel URL: `http://localhost:5174`

---

## 5. Recommended Git Workflow

1. Always verify working status before starting:
   ```bash
   git status
   ```
2. Make modular, logically cohesive commits following Conventional Commits format:
   - `feat(ingestion): add pymupdf text extractor`
   - `fix(retrieval): correct reciprocal rank fusion score computation`
   - `docs(adr): add adr-002 for chunking strategy`
3. Never commit `.env`, `venv/`, or build outputs (`dist/`).

