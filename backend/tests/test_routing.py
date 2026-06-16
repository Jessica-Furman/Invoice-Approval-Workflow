"""Tests for inbox routing (M5)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import models
from app.db.base import Base
from app.services.routing import route_invoice
from app.services.storage import LocalStorage


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'r.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _setup_dirs(tmp_path, monkeypatch):
    from app import config

    matched = tmp_path / "matched"
    flagged = tmp_path / "flagged"
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(config.settings, "INBOX_MATCHED_DIR", str(matched))
    monkeypatch.setattr(config.settings, "INBOX_FLAGGED_DIR", str(flagged))
    monkeypatch.setattr(config.settings, "STORAGE_DIR", str(storage_dir))
    return matched, flagged, LocalStorage(str(storage_dir))


def test_routes_matched_and_reroutes_on_status_change(db, tmp_path, monkeypatch):
    matched, flagged, storage = _setup_dirs(tmp_path, monkeypatch)

    # A stored PDF for the invoice.
    src = tmp_path / "INV1.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    storage.put_file(str(src), "INV1.pdf")

    inv = models.Invoice(invoice_number="INV1", status=models.STATUS_MATCHED, pdf_storage_key="INV1.pdf")
    db.add(inv)
    db.commit()

    assert route_invoice(db, inv, storage) == "matched"
    db.commit()
    assert (matched / "INV1.pdf").exists()
    assert not (flagged / "INV1.pdf").exists()
    assert inv.routed_to == "matched"

    # Status flips to flagged on re-match -> file moves, stale matched copy removed.
    inv.status = models.STATUS_FLAGGED
    assert route_invoice(db, inv, storage) == "flagged"
    db.commit()
    assert (flagged / "INV1.pdf").exists()
    assert not (matched / "INV1.pdf").exists()

    # Routing is logged.
    events = [a.event for a in db.scalars(select(models.AuditLog)).all()]
    assert events.count("routed") == 2
