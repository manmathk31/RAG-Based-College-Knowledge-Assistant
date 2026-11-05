"""Verification utility to validate foundational backend configuration and imports."""

import sys
import os

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def verify_foundation():
    print("Checking backend imports...")
    try:
        from app.core.config import get_settings
        settings = get_settings()
        print(f"  [OK] Settings loaded: {settings.PROJECT_NAME} (env: {settings.ENVIRONMENT})")

        from app.schemas.health import HealthResponse
        hr = HealthResponse(status="ok", project_name=settings.PROJECT_NAME, environment="dev", version="0.1.0")
        print(f"  [OK] Pydantic health schema: {hr.status}")

        from app.storage.base import BaseDocumentStorage
        print(f"  [OK] BaseDocumentStorage interface ready: {BaseDocumentStorage.__name__}")

        from app.vector_store.base import BaseVectorStore
        print(f"  [OK] BaseVectorStore interface ready: {BaseVectorStore.__name__}")

        from app.main import app
        print(f"  [OK] FastAPI app instance initialized: {app.title}")

        print("\nAll foundational backend checks PASSED.")
        return 0
    except Exception as e:
        print(f"\n[FAILED] Backend foundation check error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(verify_foundation())

