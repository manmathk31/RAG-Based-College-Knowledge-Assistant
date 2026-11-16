# College Knowledge Assistant — Frontend

Two independent applications are included:
- `user-app`: student-facing RAG chatbot (Vite port 5173)
- `admin-app`: document administration portal (Vite port 5174)

## Requirements
- Node.js 20+
- npm 10+
- FastAPI backend running at `http://localhost:8000`

## Student application
```bash
cd frontend/user-app
npm ci
# Copy .env.example to .env and adjust VITE_API_BASE_URL if needed
npm run dev
```
Open http://localhost:5173

## Admin application
```bash
cd frontend/admin-app
npm ci
# Copy .env.example to .env and adjust VITE_API_BASE_URL if needed
npm run dev
```
Open http://localhost:5174

The admin sign-in form asks for the API secret at runtime. It is kept in application memory and is not written into a VITE_ environment variable or bundled into static assets. **This does not make a browser-held shared secret fully confidential**: an authorized browser user can inspect requests and memory. For public production deployment, place the admin app behind a VPN/private network or implement a server-side authenticated proxy/session and role-based identity before exposing administrative endpoints.

## API contract
The student app calls `GET /health` and `POST /chat` using the backend's `message` + `history` contract. It renders citations from `sources[]`, including `citation_id`, `document_name`, `page_number`, `section`, and `snippet`.

The admin app calls `GET/POST /documents`, `DELETE /documents/{id}`, and `POST /documents/{id}/retry`, with `X-Admin-Secret` supplied at runtime. The document list uses `skip` and `limit` and reads `items`, `total`, and document fields from the backend Pydantic response.

## Build
Run `npm ci && npm run build` separately in each app directory.

## Functional features in this frontend
- Student chat sends real requests to FastAPI and displays backend answers and source citations.
- Recent conversations are retained in the current browser session; this is not server-side conversation persistence.
- Admin upload, list, status filtering, retry, delete, and dependency readiness use the documented backend endpoints.
- The admin document table refreshes periodically while the admin session is active.
- Admin API secret is requested at runtime and held in in-memory React state. For public deployment, use server-side authentication/proxy or a private admin network; a browser cannot keep a shared secret confidential.


## Guest-first access and optional student sign-in

The user application is public by default. Visitors and prospective applicants can open the chatbot and ask questions about admissions, programmes, eligibility, fees, placements, academics, and campus facilities without creating an account. Existing MITAOE students may optionally use **Student Login** for authenticated student features. The login accepts any registered email address; the backend does not enforce a college email domain. Student accounts are provisioned by an authorized administrator using `python -m scripts.create_student` from the `backend` directory.

The chat API accepts guest requests without an Authorization header. If a valid student access token is supplied, the request is associated with that student. Invalid or expired supplied tokens are rejected rather than silently treated as guest requests.
