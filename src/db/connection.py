from __future__ import annotations

import os
import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("db")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_ENABLE = os.getenv("ENABLE_DB", "false").lower() in {"1", "true", "yes"}
_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/trojan_parse",
)
_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

_engine = None
_SessionLocal: Optional[sessionmaker] = None
_db_available = False


def _build_engine():
    global _engine, _SessionLocal, _db_available
    if _engine is not None:
        return _engine
    if not _ENABLE:
        logger.info("Database disabled via ENABLE_DB env var")
        return None
    try:
        _engine = create_engine(
            _DB_URL,
            pool_size=_POOL_SIZE,
            pool_timeout=_POOL_TIMEOUT,
            echo=False,
            future=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_available = True
        logger.info("Database engine initialised")
        return _engine
    except Exception as exc:
        logger.warning(f"Database unavailable: {exc}")
        _engine = None
        _SessionLocal = None
        _db_available = False
        return None


def db_available() -> bool:
    if _engine is None and _ENABLE:
        _build_engine()
    return _db_available


@contextmanager
def get_session() -> Iterator:
    if not db_available():
        raise RuntimeError("Database not available")
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def health_check() -> bool:
    if not db_available():
        return False
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def run_sql_file(path: str) -> None:
    if not db_available():
        raise RuntimeError("Cannot run migrations: database unavailable")
    sql = open(path, "r", encoding="utf-8").read()
    with get_session() as session:
        session.execute(text(sql))
