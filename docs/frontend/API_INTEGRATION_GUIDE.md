# Frontend API Integration Guide

This guide is the authoritative integration contract for developers building the **User Chatbot** (`frontend/user-app`) and **Admin Panel** (`frontend/admin-app`) frontends.

---

## 1. Backend Overview & Architecture

The backend is a **FastAPI modular monolith** implementing a production-grade Hybrid RAG (Retrieval-Augmented Generation) pipeline:
- **Vector Store**: Qdrant Cloud storing chunk embeddings (384-dimensional) and canonical chunk payloads (page numbers, section titles, chunk text, token counts).
- **Metadata Database**: Supabase PostgreSQL acting as the document registry, tracking upload status, versions, content hashes, and a `document_chunks` table indexing full-text search vectors (`tsvector` with GIN indexing).
- **Embedding Provider**: Hugging Face hosted serverless inference (`BAAI/bge-small-en-v1.5`, 384 dimensions).
- **Generation Model**: Google Gemini (`gemini-2.5-flash` via official `google-genai` SDK) with strict grounding and zero hallucination prompts.
- **Retrieval Engine**: Hybrid Reciprocal Rank Fusion (RRF, $k=60$) combining Qdrant dense vector cosine similarity and Supabase PostgreSQL keyword search (`websearch_to_tsquery` + `ts_rank_cd`), with automatic graceful degradation.

```
                           +---------------------------+
                           |  Frontend Applications    |
                           | User Chatbot / Admin Panel|
                           +-------------+-------------+
                                         | HTTP / JSON
                                         v
                           +---------------------------+
                           |      FastAPI Backend      |
                           |   /api/v1/chat, /documents|
                           +------+-------------+------+
                                  |             |
           +----------------------+             +-----------------------+
           v                                                            v
+-----------------------+                                    +----------------------+
|  Supabase PostgreSQL  |                                    |     Qdrant Cloud     |
|   Document Registry   |                                    | 384-dim Dense Chunks |
| GIN tsvector Keywords |                                    | Payload & Filenames  |
+-----------------------+                                    +----------------------+
           ^                                                            ^
           |              +--------------------------+                  |
           +--------------+   Hybrid RRF Engine      +------------------+
                          |   Dense + Keyword Fusion |
                          +-------------+------------+
                                        | Context (<=2000 tokens)
                                        v
                          +--------------------------+
                          |  Google Gemini 2.5 Flash |
                          | Strict Grounded Response |
                          +--------------------------+
```

---

## 2. Base URLs & Environment Configuration

| Environment | Base URL | Notes |
| :--- | :--- | :--- |
| **Local Development** | `http://localhost:8000` | Default backend address |
| **API Version Prefix** | `/api/v1` | All endpoints are namespaced |
| **Interactive Docs** | `http://localhost:8000/docs` | Swagger UI OpenAPI specification |

### Environment Variables for Frontends

#### `frontend/user-app/.env`
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

#### `frontend/admin-app/.env`
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_ADMIN_API_SECRET=dev-admin-secret
```

---

## 3. Chat API Endpoint Specification

### `POST /api/v1/chat`
Endpoint for student queries against college documents. *(Note: `POST /api/v1/chat/query` is an alias providing 100% backward compatibility).*

#### Request Headers
```http
Content-Type: application/json
```

#### Request Payload
```json
{
  "message": "What is the minimum attendance requirement for semester exams?"
}
```
*Note: Both `"message"` and `"question"` keys are accepted.*

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `message` / `question` | string | Yes | Query text (1–2000 characters). Whitespace is automatically stripped. |

#### Response Payload (200 OK)
```json
{
  "answer": "According to the Academic Regulations [1], students must maintain a minimum of 75% attendance in each course to be eligible to appear for semester end examinations. A condonation of up to 10% may be granted on medical grounds [2].",
  "sources": [
    {
      "citation_id": "1",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_name": "Academic_Regulations_2025.pdf",
      "document_version": 2,
      "page_number": 14,
      "section": "Article 4.2: Attendance Requirements",
      "chunk_id": "chunk_7f8a9b1c",
      "snippet": "Students must maintain a minimum attendance of 75% in each registered course to be eligible for semester-end examinations."
    },
    {
      "citation_id": "2",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_name": "Academic_Regulations_2025.pdf",
      "document_version": 2,
      "page_number": 15,
      "section": "Article 4.3: Attendance Condonation",
      "chunk_id": "chunk_3e2d1c0b",
      "snippet": "The Dean of Academic Affairs may condone attendance shortages between 65% and 75% upon valid medical certification."
    }
  ],
  "retrieval_mode": "hybrid",
  "request_id": "req-9b8e21a4-c361-419b-a012-78d910111213"
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `answer` | string | Grounded response generated by Gemini. References context using `[1]`, `[2]`. |
| `sources` | array | Ordered list of source citations corresponding to numbers in the answer. |
| `sources[].citation_id` | string | Index marker (`"1"`, `"2"`) matching citations in the answer text. |
| `sources[].document_id` | string | UUID of the source document in Supabase. |
| `sources[].document_name` | string | Original filename of the document (e.g. `Fee_Structure_2025.pdf`). |
| `sources[].document_version` | integer | Active document version number (e.g. `1`, `2`). |
| `sources[].page_number` | integer / null | 1-based page number where the information appears. |
| `sources[].section` | string / null | Extracted heading or section title. |
| `sources[].chunk_id` | string | Unique Qdrant point ID for debugging/traceability. |
| `sources[].snippet` | string | Verbatim excerpt from the source chunk. |
| `retrieval_mode` | string | One of `"hybrid"`, `"dense_only"`, `"keyword_only"`, or `"fallback"`. |
| `request_id` | string | Unique trace ID for telemetry and error tracking. |

---

## 4. Source Citation Display Format

### How Citations Work
1. The backend guarantees that numbered brackets like `[1]`, `[2]` in `answer` map directly to the item in `sources` where `citation_id == "1"`, `citation_id == "2"`.
2. Chunks are deduplicated and trimmed to fit the 2000-token context budget.

### Recommended UI Display Pattern
1. **Interactive In-Text Badges**: Parse `\[(\d+)\]` with regex in your markdown parser. Render them as interactive pills/badges (e.g. `<span class="citation-pill">[1]</span>`).
2. **Hover / Click Popover**: Clicking or hovering on `[1]` should open a tooltip or modal displaying:
   - Document Name (e.g., `Academic_Regulations_2025.pdf`)
   - Page & Section (e.g., `Page 14 · Article 4.2`)
   - Verbatim excerpt snippet
3. **Collapsible Source Drawer**: Below each assistant message, display a list of "Sources Consulted (N)" with cards showing the document name, page badge, and snippet preview.

---

## 5. Fallback Responses (Honest Uncertainty)

When no college documents contain the answer, or when similarity scores are below relevance thresholds, the backend does not hallucinate. It responds with:

```json
{
  "answer": "I do not have enough information in the provided college documents to answer your question. Please verify with the college administration or check the uploaded student handbook.",
  "sources": [],
  "retrieval_mode": "fallback",
  "request_id": "req-8c9f02..."
}
```

**Frontend Guidance**:
- Check `sources.length === 0` or `retrieval_mode === "fallback"`.
- If true, display the answer normally and show an optional prompt: *"Need more help? Contact Academic Office at office@college.edu"*. Do not render an empty "Sources" drawer.

---

## 6. Admin API Endpoints

All admin endpoints require the `X-Admin-Secret` header.

### 1. Upload Document
`POST /api/v1/documents`
- **Request Type**: `multipart/form-data`
- **Body**: Form field `file` containing `.pdf` or `.docx` (max 50 MB).
- **Behavior**:
  - Validates MIME type and magic bytes.
  - Automatically deduplicates: if an identical file was already indexed, returns `is_duplicate: true` with existing ID without re-indexing.
  - Version increments: if a new file with the same filename is uploaded, creates version $N+1$, marks it active, deactivates older versions, and purges obsolete vectors.
- **Response** (201 Created):
```json
{
  "action": "created",
  "is_duplicate": false,
  "document": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "original_filename": "Hostel_Rules_2025.pdf",
    "normalized_filename": "hostel_rules_2025.pdf",
    "file_type": "pdf",
    "file_size": 204850,
    "content_hash": "a1b2c3d4...",
    "document_version": 1,
    "status": "completed",
    "chunk_count": 12,
    "is_active": true,
    "created_at": "2026-11-05T08:00:00Z",
    "updated_at": "2026-11-05T08:00:15Z",
    "processing_started_at": "2026-11-05T08:00:02Z",
    "processing_completed_at": "2026-11-05T08:00:15Z",
    "error_message": null
  }
}
```

### 2. List Documents
`GET /api/v1/documents`
- **Query Parameters**:
  - `page` (integer, default `1`)
  - `page_size` (integer, default `20`, max `100`)
  - `status` (string, optional: `"completed"`, `"processing"`, `"failed"`)
  - `active_only` (boolean, default `false`)
- **Response** (200 OK):
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "original_filename": "Hostel_Rules_2025.pdf",
      "normalized_filename": "hostel_rules_2025.pdf",
      "file_type": "pdf",
      "file_size": 204850,
      "content_hash": "a1b2c3d4...",
      "document_version": 1,
      "status": "completed",
      "chunk_count": 12,
      "is_active": true,
      "created_at": "2026-11-05T08:00:00Z",
      "updated_at": "2026-11-05T08:00:15Z",
      "processing_started_at": "2026-11-05T08:00:02Z",
      "processing_completed_at": "2026-11-05T08:00:15Z",
      "error_message": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 3. Get Document Details
`GET /api/v1/documents/{id}`
- **Response** (200 OK): Returns the `DocumentDetailResponse` object.

### 4. Delete Document
`DELETE /api/v1/documents/{id}`
- **Behavior**: Deletes all document versions and metadata from Supabase and purges all corresponding vector points from Qdrant Cloud.
- **Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted_versions": [1],
  "vectors_deleted": true,
  "message": "Document and 1 associated version(s) successfully deleted from database and vector store."
}
```

### 5. Retry Failed Document
`POST /api/v1/documents/{id}/retry`
- **Request Type**: `multipart/form-data`
- **Body**: Form field `file` containing the replacement `.pdf` or `.docx`.
- **Behavior**: Re-runs extraction, embedding, and indexing for a document marked with `status: "failed"`.
- **Response** (200 OK): Returns `DocumentDetailResponse`.

---

## 7. Authentication & Headers

| Header | Required For | Expected Value | Error on Failure |
| :--- | :--- | :--- | :--- |
| `Content-Type` | All POST/PUT requests | `application/json` or `multipart/form-data` | `415 Unsupported Media Type` or `422` |
| `X-Admin-Secret` | All `/api/v1/documents` endpoints | Matches backend `ADMIN_API_SECRET` | `401 Unauthorized` |

*Note: User Chatbot queries to `/api/v1/chat` do NOT require authentication or any secret header.*

---

## 8. Ingestion Statuses & Polling Strategy

When a file is uploaded, the document progresses through lifecycle statuses:
- `processing`: Document has been staged; text extraction, chunking, and embedding are executing.
- `completed`: Chunks successfully indexed in Qdrant and keywords indexed in PostgreSQL. Ready for retrieval.
- `failed`: Extraction or embedding failed. `error_message` contains the reason.

### Admin Panel Polling Pattern
When an upload returns a document with `status: "processing"`:
1. Poll `GET /api/v1/documents/{id}` every 2000ms.
2. Stop polling when `status === "completed"` or `status === "failed"`.
3. Set a timeout limit (e.g. 60 seconds) to avoid indefinite polling.

---

## 9. Error Handling & HTTP Status Codes

The backend uses standard HTTP status codes with structured JSON error responses:

```json
{
  "detail": "Descriptive error message explaining the failure."
}
```

| HTTP Status | Meaning | Typical Trigger | Recommended Frontend Action |
| :--- | :--- | :--- | :--- |
| `400 Bad Request` | Invalid client input | Empty question or corrupted file format | Display error message in form validation |
| `401 Unauthorized` | Missing/invalid secret | Missing or wrong `X-Admin-Secret` header | Prompt administrator to re-check API secret |
| `404 Not Found` | Entity missing | Document ID does not exist in registry | Remove item from table, show toast notification |
| `409 Conflict` | Document state conflict | Retrying an already completed document | Refresh document list |
| `422 Unprocessable` | Schema validation error | Missing payload field or invalid type | Inspect request body against TypeScript contract |
| `500 Server Error` | Unexpected backend bug | Unhandled internal exception | Show generic "Unexpected error. Please retry." |
| `503 Unavailable` | External service down | Both Qdrant and Supabase are unreachable, or Gemini rate-limited | Show "Service temporarily busy. Please wait a moment." |
| `504 Timeout` | Generation timeout | Gemini API timed out after 30 seconds | Show "Response timed out. Please try asking again." |

---

## 10. CORS Configuration

The backend is configured to accept requests from:
- `http://localhost:5173` (Vite User Chatbot default)
- `http://localhost:5174` (Vite Admin Panel default)

Allowed HTTP Methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`
Allowed Headers: `*` (including `Content-Type`, `X-Admin-Secret`, `Authorization`)

---

## 11. TypeScript Types & Interfaces

Copy these directly into your frontend codebases (e.g. `src/types/api.ts`):

```typescript
// ==========================================
// CHAT API CONTRACTS
// ==========================================

export interface ChatRequest {
  message: string;
}

export interface SourceCitation {
  citation_id: string;
  document_id: string;
  document_name: string;
  document_version: number;
  page_number: number | null;
  section: string | null;
  chunk_id: string;
  snippet: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  retrieval_mode: 'hybrid' | 'dense_only' | 'keyword_only' | 'fallback';
  request_id: string;
}

// ==========================================
// ADMIN DOCUMENT CONTRACTS
// ==========================================

export type DocumentStatus = 'processing' | 'completed' | 'failed';

export interface DocumentItem {
  id: string;
  original_filename: string;
  normalized_filename: string;
  file_type: 'pdf' | 'docx';
  file_size: number;
  content_hash: string;
  document_version: number;
  status: DocumentStatus;
  chunk_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  processing_started_at: string | null;
  processing_completed_at: string | null;
  error_message: string | null;
}

export interface DocumentUploadResponse {
  action: 'created' | 'version_incremented' | 'duplicate_skipped';
  is_duplicate: boolean;
  document: DocumentItem;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentDeleteResponse {
  id: string;
  deleted_versions: number[];
  vectors_deleted: boolean;
  message: string;
}

// ==========================================
// HEALTH CONTRACTS
// ==========================================

export interface HealthResponse {
  status: string;
  timestamp: string;
  environment: string;
  version: string;
}

export interface ReadinessResponse {
  status: 'ready' | 'degraded';
  services: {
    qdrant: boolean;
    database: boolean;
    huggingface: boolean;
    gemini: boolean;
  };
  details: {
    gemini_model: string;
    gemini_configured: boolean;
  };
}
```

---

## 12. Frontend API Client Examples

### User Chat Client (`fetch`)

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function askQuestion(message: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Network request failed' }));
    throw new Error(errorData.detail || `Server error: ${response.status}`);
  }

  return response.json();
}
```

### Admin Document Client (`fetch`)

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const ADMIN_SECRET = import.meta.env.VITE_ADMIN_API_SECRET || 'dev-admin-secret';

const defaultHeaders = {
  'X-Admin-Secret': ADMIN_SECRET,
};

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: 'POST',
    headers: defaultHeaders,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
}

export async function listDocuments(page = 1, pageSize = 20): Promise<DocumentListResponse> {
  const response = await fetch(`${API_BASE_URL}/documents?page=${page}&page_size=${pageSize}`, {
    headers: defaultHeaders,
  });

  if (!response.ok) {
    throw new Error(`Failed to load documents: ${response.status}`);
  }

  return response.json();
}

export async function deleteDocument(id: string): Promise<DocumentDeleteResponse> {
  const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
    method: 'DELETE',
    headers: defaultHeaders,
  });

  if (!response.ok) {
    throw new Error(`Failed to delete document: ${response.status}`);
  }

  return response.json();
}
```

---

## 13. Health & Readiness Endpoints

| Endpoint | Method | Purpose | Notes |
| :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | Basic liveness probe | Returns 200 OK when server is running |
| `/api/v1/health/ready` | `GET` | Readiness & dependency probe | Checks status of Qdrant, Supabase, Hugging Face, Gemini |

---

## 14. Step-by-Step Local Backend Startup

To start the backend locally for frontend development:

1. **Activate Python Virtual Environment**:
   ```powershell
   cd backend
   ..\venv\Scripts\Activate.ps1
   ```

2. **Verify `.env` Configuration**:
   Ensure valid credentials exist in `backend/.env`:
   ```env
   DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
   HF_TOKEN=hf_...
   QDRANT_URL=https://[CLUSTER_ID].us-east4-0.gcp.cloud.qdrant.io:6333
   QDRANT_API_KEY=...
   GEMINI_API_KEY=AIzaSy...
   ADMIN_API_SECRET=dev-admin-secret
   ```

3. **Run Database Migrations**:
   ```powershell
   alembic upgrade head
   ```

4. **Start the FastAPI Dev Server**:
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Verify Running State**:
   Open `http://localhost:8000/docs` in your browser. All chat and document endpoints should appear and be operational.

