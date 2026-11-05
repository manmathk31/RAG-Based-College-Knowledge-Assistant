# Coding Conventions & Standards

This document establishes the code quality, syntax, and architectural conventions for `RAG-Based-College-Knowledge-Assistant`.

---

## 1. Python & FastAPI Conventions

### 1.1 Python Standards
- **Style**: Follow PEP 8 style guidelines. Max line length: 100 characters.
- **Type Annotations**: All function signatures (arguments and return types) must be explicitly typed.
  ```python
  # Good
  def calculate_rrf_score(dense_rank: int, keyword_rank: int, k: int = 60) -> float:
      return (1.0 / (k + dense_rank)) + (1.0 / (k + keyword_rank))

  # Bad
  def calculate_rrf_score(dense_rank, keyword_rank, k=60):
      return (1.0 / (k + dense_rank)) + (1.0 / (k + keyword_rank))
  ```
- **Docstrings**: Provide concise Google-style docstrings for public classes and service functions.

### 1.2 FastAPI & API Architecture
- **No Business Logic in Routers**: Route handlers (`app/api/`) must only validate inputs, invoke domain services, and return validated schemas.
  ```python
  # Good
  @router.post("/query", response_model=ChatResponse)
  async def query_chat(
      request: ChatRequest,
      chat_service: ChatService = Depends(get_chat_service)
  ) -> ChatResponse:
      return await chat_service.process_query(request.question)

  # Bad: Writing retrieval queries and LLM prompts directly inside the route function.
  ```
- **Strict Pydantic Schemas**: Always use Pydantic models for request bodies and response contracts in `app/schemas/`. Use `model_config = ConfigDict(from_attributes=True)` where needed.
- **Dependency Injection**: Use FastAPI's `Depends` for providing configuration, clients, or service dependencies to allow simple mocking in unit tests.
- **Exception Handling**:
  - Raise `HTTPException` with explicit status codes and clean detail messages.
  - Never allow raw database or internal tracebacks to leak to the client.
  - Map domain exceptions to standard HTTP error schemas.

---

## 2. React & TypeScript Conventions

### 2.1 TypeScript Standards
- **Strict Typing**: Set `"strict": true` in `tsconfig.json`.
- **Avoid `any`**: Use explicit interfaces, types, or generics. If dynamic typing is unavoidable, use `unknown` with type guards.
- **Types Co-location**: Keep API contract types in `src/types/` and component-specific prop types inside the component file.
  ```typescript
  // src/types/api.ts
  export interface SourceCitation {
    documentName: string;
    pageNumber: number;
    snippet: string;
  }

  export interface ChatResponse {
    answer: string;
    sources: SourceCitation[];
  }
  ```

### 2.2 React Standards
- **Functional Components**: Use functional components with explicit TypeScript props.
  ```typescript
  interface CitationCardProps {
    citation: SourceCitation;
  }

  export const CitationCard: React.FC<CitationCardProps> = ({ citation }) => {
    return (
      <div className="rounded border border-gray-200 p-3 bg-white shadow-sm">
        <h4 className="font-semibold text-sm">{citation.documentName} (p. {citation.pageNumber})</h4>
        <p className="text-xs text-gray-600 mt-1">{citation.snippet}</p>
      </div>
    );
  };
  ```
- **Decoupled API Calls**: Never call `fetch()` or `axios` directly inside a React component. Encapsulate calls in `services/api.ts`.
- **Component Decomposition**: Keep components focused (< 150 lines). Break complex screens into small, single-responsibility components.

### 2.3 Styling Standards (Tailwind CSS)
- Use standard Tailwind utility classes.
- Follow mobile-first responsive conventions (`sm:`, `md:`, `lg:`).
- Maintain consistent color palettes:
  - Primary / Brand: Indigo / Blue for academic trust.
  - Status Indicators: Emerald (success/ready), Amber (processing/warning), Rose (error/failed).

---

## 3. Error Handling & Logging

### Backend Logging:
- Use Python's standard `logging` library configured via `app/core/logging.py`.
- Log with context: `logger.info("Chunking completed for document_id=%s, total_chunks=%d", doc_id, len(chunks))`.
- Never log raw API keys, passwords, or personal student data.

### Frontend Error Handling:
- Provide clear user-facing error banners when network requests fail.
- Implement error boundaries for unexpected UI runtime errors.

