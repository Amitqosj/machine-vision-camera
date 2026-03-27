"""Database engine/session bootstrap."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""


def _ensure_sqlite_path(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    sqlite_path = database_url.replace("sqlite:///", "", 1)
    if sqlite_path == ":memory:":
        return
    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)


def create_engine_and_session(
    database_url: str, echo: bool = False
) -> tuple[Engine, sessionmaker[Session]]:
    """Create SQLAlchemy engine and session factory."""
    _ensure_sqlite_path(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, echo=echo, future=True, connect_args=connect_args)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, session_factory


def initialize_database(engine: Engine) -> None:
    """Create all tables if they do not already exist."""
    # Local import avoids circular dependency with model definitions.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

