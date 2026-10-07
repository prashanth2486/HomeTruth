"""SQLite database for accounts. One file under data/; override with HOMETRUTH_DATABASE_URL."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from paths import DATABASE_PATH


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    override = (os.environ.get("HOMETRUTH_DATABASE_URL") or "").strip()
    if override:
        return override
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DATABASE_PATH}"


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


_URL = database_url()
engine = create_engine(_URL, connect_args=_connect_args(_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from users import User  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine(url: str | None = None) -> None:
    """Point the process at a fresh database. Used by tests."""
    global engine, SessionLocal, _URL
    engine.dispose()
    _URL = url or database_url()
    engine = create_engine(_URL, connect_args=_connect_args(_URL))
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    init_db()
