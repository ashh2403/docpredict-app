"""SQLite database engine, session factory and initialisation."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _make_engine(url: str) -> Engine:
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - trivial
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def configure(url: str) -> None:
    """(Re)configure the engine. Called on startup and by the test-suite."""
    global engine, SessionLocal
    if engine is not None:
        engine.dispose()
    engine = _make_engine(url)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    assert engine is not None, "database not configured"
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    assert SessionLocal is not None, "database not configured"
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
