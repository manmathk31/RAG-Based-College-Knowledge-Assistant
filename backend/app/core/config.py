"""Application settings and configuration management."""

import json
from functools import lru_cache
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    # Project Information
    PROJECT_NAME: str = "RAG-Based-College-Knowledge-Assistant"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Administrative Secret
    ADMIN_API_SECRET: str = "dev-admin-secret"

    # Relational Database (Supabase PostgreSQL Metadata)
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 1800

    @property
    def async_database_url(self) -> str:
        """Return the database URL with the postgresql+asyncpg:// scheme."""
        url = self.DATABASE_URL.strip()
        if not url:
            return ""
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        return url

    # Upload & Ingestion Constraints
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    INGESTION_MAX_CONCURRENT_JOBS: int = 10

    # Hosted Embeddings (Hugging Face Inference Providers)
    HF_TOKEN: str = ""
    EMBEDDING_PROVIDER: str = "huggingface"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_TIMEOUT: float = 30.0
    EMBEDDING_MAX_RETRIES: int = 3

    # Hosted LLM Generation (Google Gemini API)
    GEMINI_API_KEY: str = ""
    GEMINI_GENERATION_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_MAX_OUTPUT_TOKENS: int = 1024
    GEMINI_TIMEOUT: float = 30.0

    # Hybrid Retrieval & Reciprocal Rank Fusion (RRF)
    RETRIEVAL_DENSE_CANDIDATES: int = 10
    RETRIEVAL_KEYWORD_CANDIDATES: int = 10
    RETRIEVAL_TOP_K: int = 5
    RRF_K: int = 60
    MAX_CONTEXT_TOKENS: int = 2000

    # Vector Database (Qdrant Cloud)
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "college_knowledge_base"
    QDRANT_TIMEOUT: float = 10.0

    # Ingestion & Chunking Defaults
    CHUNK_SIZE: int = 600  # Target tokens
    CHUNK_OVERLAP: int = 100  # Token overlap
    TOKENIZER_ENCODING: str = "cl100k_base"
    OCR_ENABLED: bool = True
    OCR_MIN_PAGE_CHARS: int = 50  # Pages with fewer chars trigger selective OCR
    OCR_DPI: int = 300  # DPI for rendering scanned PDF pages for Tesseract
    TESSERACT_CMD: str = "tesseract"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()
