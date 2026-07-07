"""SQLAlchemy engine, session factory, and declarative Base.

SQLite locally; swap DATABASE_URL to Postgres later with no model changes.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    # check_same_thread is a SQLite-only arg; needed for FastAPI's threaded requests.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_columns() -> None:
    """Lightweight migration: add columns introduced after a DB was first created.

    We use create_all (no Alembic) for the MVP, and create_all never ALTERs existing tables — so a
    column added to a model later won't appear on an old DB. This adds any missing ones idempotently.
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "invoices" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("invoices")}
    coltype = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
    migrations = {
        "archived_at": f"ADD COLUMN archived_at {coltype}",
        # Backfill existing rows to the contractor pipeline; "other" is set only by ingest_other_pdf.
        "invoice_type": "ADD COLUMN invoice_type VARCHAR(32) DEFAULT 'contractor'",
    }
    for name, ddl in migrations.items():
        if name not in existing:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE invoices {ddl}"))


def init_db() -> None:
    """Create all tables. (Alembic migrations come later; create_all is fine for the MVP.)"""
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
