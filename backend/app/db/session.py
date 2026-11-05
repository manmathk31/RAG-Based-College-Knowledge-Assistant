"""Database session and async engine management for Supabase PostgreSQL."""

import logging
from typing import AsyncGenerator, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.core.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _prepare_asyncpg_url(raw_url: str) -> str:
    """Ensure database URL has postgresql+asyncpg scheme and clean parameters."""
    if not raw_url:
        return ""

    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # asyncpg expects 'ssl' rather than 'sslmode'
    if "sslmode" in query_params:
        ssl_val = query_params.pop("sslmode")[0]
        if "ssl" not in query_params:
            query_params["ssl"] = [ssl_val]

    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def init_db(settings: Optional[Settings] = None) -> Optional[AsyncEngine]:
    """Initialize the asynchronous SQLAlchemy engine and session factory."""
    global _engine, _session_factory

    app_settings = settings or get_settings()
    db_url = _prepare_asyncpg_url(app_settings.DATABASE_URL)

    if not db_url:
        logger.info("No DATABASE_URL configured. Database integration running in detached/disabled mode.")
        _engine = None
        _session_factory = None
        return None

    try:
        connect_args = {}
        # If connecting to cloud Supabase host, default to SSL require if not explicitly set
        if "supabase" in db_url and "ssl=" not in db_url:
            connect_args["ssl"] = "require"

        _engine = create_async_engine(
            db_url,
            pool_size=app_settings.DB_POOL_SIZE,
            max_overflow=app_settings.DB_MAX_OVERFLOW,
            pool_timeout=app_settings.DB_POOL_TIMEOUT,
            pool_recycle=app_settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,
            connect_args=connect_args,
            echo=False,
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Database engine initialized successfully.")
        return _engine
    except Exception as exc:
        logger.error("Failed to initialize database engine: %s", exc)
        _engine = None
        _session_factory = None
        return None


async def close_db() -> None:
    """Dispose of the database engine and clean up connection pool."""
    global _engine, _session_factory
    if _engine is not None:
        try:
            await _engine.dispose()
            logger.info("Database engine connections disposed.")
        except Exception as exc:
            logger.warning("Error disposing database engine: %s", exc)
        finally:
            _engine = None
            _session_factory = None


async def check_db_connectivity() -> bool:
    """Execute a simple query to verify database reachability without exposing secrets."""
    global _engine
    if _engine is None:
        return False

    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session.

    Raises:
        DatabaseUnavailableError: If database is not configured or engine failed.
    """
    global _session_factory
    if _session_factory is None:
        raise DatabaseUnavailableError(
            "Relational metadata database is currently unavailable or not configured. "
            "Please check Supabase connection settings."
        )

    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

