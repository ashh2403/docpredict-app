"""SQLite database engine, session factory and initialisation."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    """Accept the plain postgres URLs that hosts such as Neon or Render provide.

    SQLAlchemy needs the driver named explicitly to use psycopg 3.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _make_engine(url: str) -> Engine:
    url = normalize_url(url)
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
    if is_sqlite(url):
        engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(
            url,
            pool_pre_ping=True,   # hosted Postgres (e.g. Neon) closes idle connections
            pool_recycle=300,
            pool_size=5,
            max_overflow=5,
            # No server-side prepared statements: safe behind PgBouncer-style connection poolers.
            connect_args={"prepare_threshold": None},
        )

    if is_sqlite(url):
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
