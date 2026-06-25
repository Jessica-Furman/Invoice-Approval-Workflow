"""Tests for bulk export (Export All slider) + History + board archiving."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.api.invoices import bulk_export_matched, dashboard, history
from app.db.base import Base
from app.utils.names import normalize_name


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'h.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _matched_inv(db: Session, number: str) -> models.Invoice:
    ts = models.ClarityTimesheet(
        contractor_name="Jane Doe", contractor_name_normalized=normalize_name("Jane Doe"),
        hours=40.0, date_worked=date(2026, 5, 1), is_posted=True, is_time_off=False,
        project_id="PR1", capex_opex="CAPEX", source_row_hash=f"ts-{number}",
    )
    db.add(ts); db.flush()
    inv = models.Invoice(
        vendor_name="AVASOFT", invoice_number=number, status=models.STATUS_MATCHED,
        date_received=date(2026, 5, 31),
        payment_period_start=date(2026, 5, 1), payment_period_end=date(2026, 5, 31),
        line_items=[models.InvoiceLineItem(
            contractor_name="Jane Doe", contractor_name_normalized=normalize_name("Jane Doe"),
            hours=40.0, rate=95.0, amount=3800.0, line_status=models.STATUS_MATCHED,
            matched_clarity_id=ts.id, diff={"clarity_hours": 40.0},
        )],
    )
    db.add(inv); db.commit(); db.refresh(inv)
    return inv


def test_bulk_export_archives_matched_and_clears_board(db: Session):
    m1, m2 = _matched_inv(db, "INV-1"), _matched_inv(db, "INV-2")
    db.add(models.Invoice(vendor_name="X", invoice_number="FLAG-1", status=models.STATUS_FLAGGED))
    db.commit()

    assert {s.invoice_number for s in dashboard(db).matched} == {"INV-1", "INV-2"}

    bulk_export_matched(db)  # the "Export All" action

    db.refresh(m1); db.refresh(m2)
    assert m1.archived_at is not None and m2.archived_at is not None
    assert m1.coupa_csv_generated_at is not None

    board = dashboard(db)
    assert board.matched == []                                    # cleared from Matched
    assert [s.invoice_number for s in board.flagged] == ["FLAG-1"]  # flagged untouched
    assert all(s.invoice_number != "INV-1" for s in board.all)    # cleared from All too


def test_history_keeps_archived_but_board_does_not(db: Session):
    m1 = _matched_inv(db, "INV-1")
    bulk_export_matched(db)

    # Still present in History (archived), absent from the board.
    hist = {s.invoice_number: s for s in history(db)}
    assert "INV-1" in hist and hist["INV-1"].archived_at is not None
    assert dashboard(db).matched == []


def test_bulk_export_with_no_matched_raises_409(db: Session):
    db.add(models.Invoice(vendor_name="X", invoice_number="FLAG-1", status=models.STATUS_FLAGGED))
    db.commit()
    with pytest.raises(HTTPException) as e:
        bulk_export_matched(db)
    assert e.value.status_code == 409
