"""Tests for the name+hours matching engine (M4)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db.base import Base
from app.services.matching import ClarityIndex, match_invoice
from app.utils.names import normalize_name


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'m.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _ts(db, name, hours, project="PR1", worked=date(2026, 5, 1), time_off=False, posted=True):
    db.add(models.ClarityTimesheet(
        contractor_name=name, contractor_name_normalized=normalize_name(name),
        hours=hours, date_worked=worked, is_time_off=time_off, is_posted=posted,
        period_start=date(2026, 4, 26), period_end=date(2026, 5, 30),
        project_id=project,
        source_row_hash=f"{name}-{hours}-{project}-{worked}-{int(time_off)}-{int(posted)}",
    ))


def _invoice(db, lines):
    inv = models.Invoice(
        vendor_name="Acme", invoice_number="INV1", status=models.STATUS_NEEDS_REVIEW,
        payment_period_start=date(2026, 4, 26), payment_period_end=date(2026, 5, 30),
        line_items=[
            models.InvoiceLineItem(
                contractor_name=n,
                contractor_name_normalized=normalize_name(n),
                hours=h,
            )
            for n, h in lines
        ],
    )
    db.add(inv)
    db.commit()
    return inv


def test_exact_match_sets_matched(db: Session):
    _ts(db, "Jane Doe", 80)
    db.commit()
    inv = _invoice(db, [("Jane Doe", 80)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    assert inv.line_items[0].line_status == models.STATUS_MATCHED
    assert inv.status == models.STATUS_MATCHED


def test_hours_mismatch_flags(db: Session):
    _ts(db, "Jane Doe", 80)
    db.commit()
    inv = _invoice(db, [("Jane Doe", 120)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    li = inv.line_items[0]
    assert li.line_status == models.STATUS_FLAGGED
    assert li.diff["clarity_hours"] == 80
    assert inv.status == models.STATUS_FLAGGED


def test_unresolved_name_flags(db: Session):
    _ts(db, "Jane Doe", 80)
    db.commit()
    inv = _invoice(db, [("Totally Different Person", 80)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    assert inv.line_items[0].line_status == models.STATUS_FLAGGED
    assert inv.line_items[0].diff["match_method"] == "unresolved"


def test_crossref_resolves_name_variant(db: Session):
    # Clarity has "John Moore"; invoice says "John Doe"; cross-ref maps them.
    _ts(db, "John Moore", 100)
    db.add(models.NameCrossref(invoice_name="John Doe", clarity_name="John Moore"))
    db.commit()
    inv = _invoice(db, [("John Doe", 100)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    li = inv.line_items[0]
    assert li.line_status == models.STATUS_MATCHED
    assert li.diff["match_method"] == "crossref"


def test_pending_posting_reason_when_time_not_posted(db: Session):
    # In-period: 24h posted + 48h submitted (not posted). Invoice bills 72h.
    _ts(db, "Jane Doe", 24, worked=date(2026, 5, 2), posted=True)
    _ts(db, "Jane Doe", 48, worked=date(2026, 5, 9), posted=False)  # submitted, awaiting posting
    db.commit()
    inv = _invoice(db, [("Jane Doe", 72)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    li = inv.line_items[0]
    assert li.line_status == models.STATUS_FLAGGED
    assert li.diff["clarity_hours"] == 24.0
    assert li.diff["clarity_pending_hours"] == 48.0
    assert li.diff["pending_posting"] is True
    assert "awaiting posting" in inv.mismatch_reasons[0]["reason"]


def test_real_discrepancy_not_flagged_as_pending(db: Session):
    # Posted 50, no pending; invoice bills 120 -> a genuine discrepancy, not a posting-timing issue.
    _ts(db, "Jane Doe", 50, posted=True)
    db.commit()
    inv = _invoice(db, [("Jane Doe", 120)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    li = inv.line_items[0]
    assert li.diff["pending_posting"] is False
    assert "awaiting posting" not in inv.mismatch_reasons[0]["reason"]


def test_time_off_posted_and_date_filters(db: Session):
    # Billable in-period: 60 + 20 = 80. Excluded: time-off (8), non-posted (10), out-of-period (40).
    _ts(db, "Jane Doe", 60, worked=date(2026, 5, 1))
    _ts(db, "Jane Doe", 20, worked=date(2026, 5, 10))
    _ts(db, "Jane Doe", 8, worked=date(2026, 5, 12), time_off=True)
    _ts(db, "Jane Doe", 10, worked=date(2026, 5, 13), posted=False)  # not posted
    _ts(db, "Jane Doe", 40, worked=date(2026, 6, 15))  # outside invoice period
    db.commit()
    inv = _invoice(db, [("Jane Doe", 80)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    li = inv.line_items[0]
    assert li.diff["clarity_hours"] == 80.0
    assert li.line_status == models.STATUS_MATCHED


def test_fuzzy_match_minor_spelling(db: Session):
    _ts(db, "Jonathan Smith", 50)
    db.commit()
    inv = _invoice(db, [("Jonathan Smyth", 50)])  # one letter off
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    assert inv.line_items[0].line_status == models.STATUS_MATCHED
    assert inv.line_items[0].diff["match_method"] == "fuzzy"


def test_order_insensitive_exact_match(db: Session):
    # Clarity "Chaitra, Gurijala" -> first/last flip -> "Gurijala Chaitra"; invoice "Gurijala Chaitra".
    # (Construct the reversed token order directly to prove order-independence.)
    _ts(db, "Chaitra Gurijala", 200)
    db.commit()
    inv = _invoice(db, [("Gurijala Chaitra", 200)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    li = inv.line_items[0]
    assert li.line_status == models.STATUS_MATCHED
    assert li.diff["match_method"] == "exact"


def test_near_miss_uses_fuzzy_not_no_match(db: Session):
    _ts(db, "Aishwarya Viswanathan", 200)
    db.commit()
    inv = _invoice(db, [("Aishwarya Viswanthan", 200)])  # one letter dropped (~95% token_sort)
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    li = inv.line_items[0]
    assert li.diff["match_method"] == "fuzzy"
    assert li.line_status == models.STATUS_MATCHED


def test_fuzzy_resolves_partial_and_variant_names(db: Session):
    # Real AVASOFT cases: invoice carries a shortened / concatenated / split name; Clarity has the
    # full name. These must resolve via fuzzy (shared name component) instead of flagging.
    _ts(db, "Azarudeen Shariff", 160)            # invoice has only the first name
    _ts(db, "Sreenithi Saravana Perumal", 160)   # invoice concatenates "SaravanaPerumal"
    _ts(db, "Srisoorya Sivakumar", 160)          # invoice splits + drops surname -> "Sri Soorya"
    db.commit()
    for invoice_name in ("Azarudeen", "Sreenithi SaravanaPerumal", "Sri Soorya"):
        inv = _invoice(db, [(invoice_name, 160)])
        match_invoice(db, inv, ClarityIndex.build(db))
        db.commit()
        li = inv.line_items[0]
        assert li.line_status == models.STATUS_MATCHED, invoice_name
        assert li.diff["match_method"] == "fuzzy", invoice_name


def test_unrelated_name_does_not_fuzzy_match(db: Session):
    # A name not in Clarity must NOT be force-matched to a coincidental near-name.
    _ts(db, "Jon Nelson", 100)
    db.commit()
    inv = _invoice(db, [("Michael Johnson", 100)])
    match_invoice(db, inv, ClarityIndex.build(db))
    db.commit()
    assert inv.line_items[0].diff["match_method"] == "unresolved"
