# Testing Strategy & Policy

## 1. Core Testing Philosophy

Our testing strategy balances high code quality and software reliability with high developer velocity. Repeatedly running full test suites after every tiny character edit or creating hundreds of trivial mock tests wastes time and produces false confidence.

Instead, we follow a **focused, milestone-oriented testing policy**:
- Test when meaningful boundaries are crossed.
- Test what is prone to subtle failure (chunking boundaries, ranking math, serialization, schema validation).
- Never claim tests passed unless they were physically executed and verified in the terminal.

---

## 2. The 10 Engineering Rules of Testing

Every human engineer and AI coding agent working in this repository must strictly observe these 10 rules:

1. **Do not run the entire test suite after every small edit**: Save full runs for milestone verification.
2. **Use code inspection and focused checks during normal development**: Validate syntax, types, and logic flow via careful review before invoking runners.
3. **Run targeted tests when completing a meaningful module**: When finishing chunking logic, run only `pytest tests/test_chunking.py`.
4. **Run integration tests after connecting major modules**: Run contract and integration checks when bridging Ingestion to Qdrant or Retrieval to Gemini.
5. **Run a complete test suite at major milestones**: Execute full suite verification prior to marking major milestones as complete in `PROJECT_STATUS.md`.
6. **Run final end-to-end smoke tests before considering the application ready**: Verify the entire loop (upload document -> retrieve -> generate answer with citations).
7. **Never claim that tests passed unless they were actually executed**: False claims about test results are strictly forbidden. Report actual command outputs.
8. **Never repeatedly rerun the same failing test without understanding and fixing the underlying cause**: Form a hypothesis, inspect logs, fix the bug, and only then re-execute the test.
9. **Do not create meaningless tests simply to increase test count**: Do not write tests that merely assert `1 == 1` or mock out the entirety of the unit under test.
10. **Prioritize high-value test areas**:
    - File format extraction accuracy (PDF text, tables, OCR fallback triggers).
    - Chunking boundary and overlap precision (no lost words, correct offset calculation).
    - Reciprocal Rank Fusion (RRF) math and deduplication.
    - Source attribution integrity (every retrieved chunk has traceable document and page metadata).
    - API contract adherence (Pydantic schema validation and error responses).
    - Failure and edge cases (unsupported file formats, corrupted PDFs, missing API keys).

---

## 3. Test Structure & Organization

All backend tests are located in `backend/tests/`:

```text
backend/tests/
├── conftest.py               # Shared fixtures, test client, mocked settings
├── test_health.py            # Basic API health check contract verification
├── test_extraction.py        # (Planned) PyMuPDF & python-docx extraction tests
├── test_chunking.py          # (Planned) Recursive structure-aware chunking tests
├── test_retrieval.py         # (Planned) RRF fusion math & keyword retrieval tests
└── test_api_contracts.py     # (Planned) Endpoint request/response validation tests
```

---

## 4. Execution Commands

### Run Only Health Check Tests:
```powershell
cd backend
..\venv\Scripts\pytest.exe tests/test_health.py -v
```

### Run a Single Targeted Test File:
```powershell
..\venv\Scripts\pytest.exe tests/test_chunking.py -v
```

### Run Full Backend Test Suite (Milestone Gate):
```powershell
..\venv\Scripts\pytest.exe tests/ -v
```

### Frontend Type and Build Validation:
```powershell
# User Frontend
cd frontend/user-app
npm run build

# Admin Frontend
cd frontend/admin-app
npm run build
```

