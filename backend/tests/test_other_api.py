"""Tests for the Other-invoices API + type isolation from the contractor board."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.api.invoices import dashboard, delete_invoice, history
from app.api.other_invoices import (
    other_dashboard,
    other_history,
    other_invoice_detail,
)
from app.db.base import Base


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'o.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _other(db: Session, *, number: str, status: str, supplier: str | None, missing: list[str]) -> models.Invoice:
    inv = models.Invoice(
        invoice_type=models.INVOICE_TYPE_OTHER,
        vendor_name="GitHub, Inc",
        invoice_number=number,
        date_received=date(2026, 6, 1),
        total_invoice_cost=100.0,
        status=status,
        raw_extraction={"supplier_number": supplier},
        mismatch_reasons=[{"field": f, "reason": "x", "invoice_value": None, "clarity_value": None} for f in missing],
        line_items=[models.InvoiceLineItem(contractor_name="Copilot usage", hours=None, rate=None, amount=100.0)],
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def _contractor(db: Session) -> models.Invoice:
    inv = models.Invoice(
        vendor_name="AVASOFT", invoice_number="INV-C1", status=models.STATUS_MATCHED,
        date_received=date(2026, 5, 31),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def test_dashboard_splits_found_and_missing(db: Session):
    _other(db, number="A1", status=models.STATUS_ALL_DATA_FOUND, supplier="RAC-1", missing=[])
    _other(db, number="A2", status=models.STATUS_MISSING_DATA, supplier=None, missing=["supplier number"])
    resp = other_dashboard(db)
    assert len(resp.found) == 1 and len(resp.missing) == 1 and len(resp.all) == 2
    assert resp.found[0].supplier_number == "RAC-1"
    assert resp.missing[0].missing_count == 1


def test_cost_center_and_offset_gl_surface_from_raw(db: Session):
    inv = _other(db, number="A6", status=models.STATUS_ALL_DATA_FOUND, supplier="RAC-1", missing=[])
    inv.raw_extraction = {**inv.raw_extraction, "cost_center": "DT600, 99940", "offset_gl_account": "679030"}
    db.commit()
    # Present on both the board summary and the detail payload.
    summary = next(s for s in other_dashboard(db).all if s.id == inv.id)
    assert summary.cost_center == "DT600, 99940" and summary.offset_gl_account == "679030"
    det = other_invoice_detail(inv.id, db)
    assert det.cost_center == "DT600, 99940" and det.offset_gl_account == "679030"


def test_budget_id_and_approver_surface_from_raw(db: Session):
    inv = _other(db, number="A7", status=models.STATUS_ALL_DATA_FOUND, supplier="RAC-1", missing=[])
    inv.raw_extraction = {**inv.raw_extraction, "budget_id": "BUD-00046", "approver": "Farooq Buvvaji"}
    db.commit()
    summary = next(s for s in other_dashboard(db).all if s.id == inv.id)
    assert summary.budget_id == "BUD-00046" and summary.approver == "Farooq Buvvaji"
    det = other_invoice_detail(inv.id, db)
    assert det.budget_id == "BUD-00046" and det.approver == "Farooq Buvvaji"


def test_detail_returns_lines_and_missing_fields(db: Session):
    inv = _other(db, number="A3", status=models.STATUS_MISSING_DATA, supplier=None, missing=["supplier number"])
    det = other_invoice_detail(inv.id, db)
    assert det.supplier_number is None
    assert det.missing_fields == ["supplier number"]
    assert len(det.line_items) == 1
    assert det.line_items[0].description == "Copilot usage" and det.line_items[0].amount == 100.0


def test_other_and_contractor_boards_are_isolated(db: Session):
    _other(db, number="A4", status=models.STATUS_ALL_DATA_FOUND, supplier="RAC-1", missing=[])
    _contractor(db)
    # Contractor board/history exclude the "other" invoice...
    assert all(s.invoice_number != "A4" for s in dashboard(db).all)
    assert all(s.invoice_number != "A4" for s in history(db))
    # ...and the other board/history exclude the contractor invoice.
    assert all(s.invoice_number != "INV-C1" for s in other_dashboard(db).all)
    assert all(s.invoice_number != "INV-C1" for s in other_history(db))


def test_delete_removes_an_other_invoice(db: Session):
    inv = _other(db, number="A5", status=models.STATUS_ALL_DATA_FOUND, supplier="RAC-1", missing=[])
    delete_invoice(inv.id, db)
    assert other_dashboard(db).all == []


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[2] / "documentation" / "Hardware_and_software_invoices").exists(),
    reason="sample invoices not present",
)
def test_ingest_other_pdf_end_to_end(db: Session, tmp_path: Path):
    """Full path: ingest a real sample PDF -> it lands as an 'other' invoice with a status + lines."""
    from app.services.ingestion import ingest_other_pdf
    from app.services.storage import LocalStorage

    sample = (
        Path(__file__).resolve().parents[2]
        / "documentation" / "Hardware_and_software_invoices" / "GitHub_INV138442106.pdf"
    )
    if not sample.exists():
        pytest.skip("GitHub sample absent")
    inv = ingest_other_pdf(db, str(sample), storage=LocalStorage(str(tmp_path)))
    assert inv.invoice_type == models.INVOICE_TYPE_OTHER
    assert inv.status in (models.STATUS_ALL_DATA_FOUND, models.STATUS_MISSING_DATA)
    assert inv.total_invoice_cost == 4735.31
    assert len(inv.line_items) == 3
    # Appears only on the other board, never the contractor one.
    assert any(s.id == inv.id for s in other_dashboard(db).all)
    assert all(s.id != inv.id for s in dashboard(db).all)
