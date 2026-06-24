"""Tests for Coupa import-CSV generation (M6)."""
from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db.base import Base
from app.services.coupa import (
    INVOICE_HEADER_COLUMNS,
    INVOICE_LINE_COLUMNS,
    build_header_row,
    coupa_csv_bytes,
)
from app.utils.names import normalize_name


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'c.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _matched_invoice(
    db: Session, *, investment: str = "Project Alpha", capex: str = "CAPEX"
) -> models.Invoice:
    ts = models.ClarityTimesheet(
        contractor_name="Jane Doe", contractor_name_normalized=normalize_name("Jane Doe"),
        hours=40.0, date_worked=date(2026, 5, 1), is_posted=True, is_time_off=False,
        project_id="PR1", investment_name=investment, capex_opex=capex,
        source_row_hash="ts1",
    )
    db.add(ts)
    db.flush()
    inv = models.Invoice(
        vendor_name="AVASOFT", invoice_number="INV-100", status=models.STATUS_MATCHED,
        date_received=date(2026, 5, 31), total_invoice_cost=3800.0,
        payment_period_start=date(2026, 5, 1), payment_period_end=date(2026, 5, 31),
        line_items=[
            models.InvoiceLineItem(
                contractor_name="Jane Doe",
                contractor_name_normalized=normalize_name("Jane Doe"),
                hours=40.0, rate=95.0, amount=3800.0,
                line_status=models.STATUS_MATCHED, matched_clarity_id=ts.id,
                diff={"clarity_hours": 40.0},
            )
        ],
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def _parse(data: bytes) -> list[list[str]]:
    text = data.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def test_csv_has_schema_rows_then_header_then_lines(db: Session):
    inv = _matched_invoice(db)
    rows = _parse(coupa_csv_bytes(inv, db))
    assert rows[0] == INVOICE_HEADER_COLUMNS         # schema row 1
    assert rows[1] == INVOICE_LINE_COLUMNS           # schema row 2
    assert rows[2][0] == "Invoice"                   # header data row
    assert rows[3][0] == "Invoice Line"              # one line data row
    assert len(rows) == 4                            # single-line invoice


def test_header_values_and_tax_defaults(db: Session):
    inv = _matched_invoice(db)
    h = build_header_row(inv)
    assert h["Invoice Number"] == "INV-100"
    assert h["Supplier Name"] == "AVASOFT"
    assert h["Invoice Date"] == "05/31/2026"
    assert h["Currency"] == "USD"
    assert h["Submit For Approval?"] == "no"
    assert h["Line Level Taxation"] == "no"
    assert h["Taxes In Origin Country Currency"] == "0.00"
    assert h["Local Currency Net"] == "3800.00"
    # Blueprint dropped Local Currency Gross / Attachment 1; added Image Scan Url.
    assert "Local Currency Gross" not in INVOICE_HEADER_COLUMNS
    assert "Image Scan Url" in INVOICE_HEADER_COLUMNS


def test_line_maps_hours_rate_and_description(db: Session):
    inv = _matched_invoice(db)
    rows = _parse(coupa_csv_bytes(inv, db))
    line = dict(zip(INVOICE_LINE_COLUMNS, rows[3]))
    assert line["Quantity"] == "40"
    assert line["Price"] == "95.00"
    assert line["Unit of Measure"] == "HOUR"
    assert line["Category"] == "Contractor Services"
    # Description = contractor - project - period
    assert "Jane Doe" in line["Description"]
    assert "Project Alpha" in line["Description"]
    assert "05/01/2026-05/31/2026" in line["Description"]


def test_capex_segments_map_to_gl_code_and_label(db: Session):
    # "Project Alpha" has no RAC/ACIMA signal -> company segments fall back to placeholders.
    inv = _matched_invoice(db, investment="Project Alpha", capex="CAPEX")
    line = dict(zip(INVOICE_LINE_COLUMNS, _parse(coupa_csv_bytes(inv, db))[3]))
    assert line["Account Segment 1"] == "<<COMPANY_CODE>>"
    assert line["Account Segment 2"] == "<<COST_CENTER>>"
    assert line["Account Segment 3"] == "246010"   # CAPEX GL code
    assert line["Account Segment 4"] == "CAPEX"     # label


def test_rac_project_maps_company_and_cost_center(db: Session):
    inv = _matched_invoice(db, investment="RACPad Time Zone Sync - Phase 1", capex="OPEX")
    line = dict(zip(INVOICE_LINE_COLUMNS, _parse(coupa_csv_bytes(inv, db))[3]))
    assert line["Account Segment 1"] == "5"        # RAC company code
    assert line["Account Segment 2"] == "H0003"    # RAC cost center
    assert line["Account Segment 3"] == "667070"   # OPEX GL code
    assert line["Account Segment 4"] == "OPEX"


def test_acima_project_maps_company_and_cost_center(db: Session):
    inv = _matched_invoice(db, investment="Acima Mobile App Replatform - All Phases", capex="CAPEX")
    line = dict(zip(INVOICE_LINE_COLUMNS, _parse(coupa_csv_bytes(inv, db))[3]))
    assert line["Account Segment 1"] == "67"       # ACIMA company code
    assert line["Account Segment 2"] == "AC000"    # ACIMA cost center


def test_unknown_fields_are_placeholder_tokens(db: Session):
    inv = _matched_invoice(db)
    h = build_header_row(inv)
    assert h["Chart of Accounts"] == "<<CHART_OF_ACCOUNTS>>"
    assert h["Requester Email"] == "<<APPROVER_EMAIL>>"
    assert h["Supplier Number"] == "<<SUPPLIER_NUMBER>>"


def test_multi_line_invoice_emits_a_row_per_contractor(db: Session):
    inv = _matched_invoice(db)
    inv.line_items.append(
        models.InvoiceLineItem(
            contractor_name="John Roe",
            contractor_name_normalized=normalize_name("John Roe"),
            hours=20.0, rate=80.0, amount=1600.0, line_status=models.STATUS_MATCHED,
        )
    )
    db.commit()
    rows = _parse(coupa_csv_bytes(inv, db))
    line_rows = [r for r in rows[2:] if r[0] == "Invoice Line"]  # skip the two schema rows
    assert len(line_rows) == 2
    assert line_rows[0][4] == "1" and line_rows[1][4] == "2"  # Line Number increments
