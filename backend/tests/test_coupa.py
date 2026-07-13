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
import app.services.coupa as coupa
from app.services.coupa import (
    INVOICE_HEADER_COLUMNS,
    INVOICE_LINE_COLUMNS,
    build_header_row,
    coupa_csv_bytes,
    coupa_csv_filename,
    supplier_number_for,
    _load_project_company_map,
    _load_supplier_index,
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


def test_header_values_and_defaults(db: Session):
    inv = _matched_invoice(db)
    h = build_header_row(inv)
    assert h["Invoice Number*"] == "INV-100"
    assert h["Supplier Name"] == "AVASOFT"
    assert h["Invoice Date*"] == "05/31/2026"
    assert h["Currency"] == "USD"
    assert h["Submit For Approval?"] == "No"
    assert h["Line Level Taxation*"] == "no"
    assert h["Status"] == ""                     # Status must be blank (never "Draft")
    # Full Coupa template: exactly the sample workbook's 177 / 73 columns, with asterisks kept.
    assert len(INVOICE_HEADER_COLUMNS) == 177 and INVOICE_HEADER_COLUMNS[0] == "Invoice"
    assert len(INVOICE_LINE_COLUMNS) == 73 and INVOICE_LINE_COLUMNS[0] == "Invoice Line"
    assert "Chart of Accounts*" in INVOICE_HEADER_COLUMNS
    assert "Description*" in INVOICE_LINE_COLUMNS and "Price*" in INVOICE_LINE_COLUMNS


def test_line_maps_hours_rate_and_description(db: Session):
    inv = _matched_invoice(db)
    rows = _parse(coupa_csv_bytes(inv, db))
    line = dict(zip(INVOICE_LINE_COLUMNS, rows[3]))
    assert line["Quantity"] == "40"                 # hours
    assert line["Price*"] == "95.00"                # rate; Coupa computes total = price x qty
    assert line["Unit of Measure*"] == "EA"
    assert line["PO Number"] == "" and line["PO Line Number"] == ""  # PO columns left blank
    # Description = contractor - project - period
    assert "Jane Doe" in line["Description*"]
    assert "Project Alpha" in line["Description*"]
    assert "05/01/2026-05/31/2026" in line["Description*"]


def test_capex_segment_is_code_only_and_unresolved_company_is_blank(db: Session):
    # "Project Alpha" has no RAC/ACIMA signal -> company segments are left BLANK (no placeholders).
    inv = _matched_invoice(db, investment="Project Alpha", capex="CAPEX")
    line = dict(zip(INVOICE_LINE_COLUMNS, _parse(coupa_csv_bytes(inv, db))[3]))
    assert line["Account Segment 1"] == ""         # company unresolved -> blank
    assert line["Account Segment 2"] == ""
    assert line["Account Segment 3"] == "246010"   # CAPEX GL code (code only)
    assert line["Account Segment 4"] == ""         # no CapEx/OpEx label is written


def test_rac_project_maps_company_and_cost_center(db: Session):
    inv = _matched_invoice(db, investment="RACPad Time Zone Sync - Phase 1", capex="OPEX")
    line = dict(zip(INVOICE_LINE_COLUMNS, _parse(coupa_csv_bytes(inv, db))[3]))
    assert line["Account Segment 1"] == "5"        # RAC company code
    assert line["Account Segment 2"] == "H0003"    # RAC cost center
    assert line["Account Segment 3"] == "667070"   # OPEX GL code


def test_acima_project_maps_company_and_cost_center(db: Session):
    inv = _matched_invoice(db, investment="Acima Mobile App Replatform - All Phases", capex="CAPEX")
    line = dict(zip(INVOICE_LINE_COLUMNS, _parse(coupa_csv_bytes(inv, db))[3]))
    assert line["Account Segment 1"] == "67"       # ACIMA company code
    assert line["Account Segment 2"] == "AC000"    # ACIMA cost center


def test_filename_is_vendor_plus_invoice_number(db: Session):
    inv = _matched_invoice(db)
    assert coupa_csv_filename(inv) == "AVASOFT_INV-100.csv"


def test_filename_strips_illegal_characters(db: Session):
    inv = _matched_invoice(db)
    inv.vendor_name = "Odyssey Information Services, Inc."
    inv.invoice_number = "61805/A"
    # commas kept; path-illegal "/" removed; trailing "." trimmed; vendor and number joined by "_".
    assert coupa_csv_filename(inv) == "Odyssey Information Services, Inc_61805A.csv"


def test_load_project_company_map_from_lob(db: Session, tmp_path):
    csv_path = tmp_path / "Company_by_Project.csv"
    csv_path.write_text(
        "Project Name,Project ID,Line of Business\n"
        "Alpha,PR001,/Upbound/RAC\n"
        "Beta,PR002,/Upbound\n"            # bare /Upbound -> RAC
        "Gamma,PR003,/Upbound/Acima\n"     # note the file uses 'Acima' casing
        "Delta,PR004,\n"                   # blank LOB -> unmapped
        ",PR005,/Upbound/RAC\n",           # kept (has a project id)
        encoding="utf-8",
    )
    m = _load_project_company_map(csv_path)
    assert m["PR001"] == "RAC"
    assert m["PR002"] == "RAC"
    assert m["PR003"] == "ACIMA"
    assert "PR004" not in m


def test_company_segments_resolved_by_project_id(db: Session, monkeypatch):
    # A real Project ID in the mapping drives company code + cost center, regardless of project name.
    import app.services.coupa as coupa
    monkeypatch.setattr(coupa, "_project_company_map", lambda: {"PR999": "ACIMA"})
    ts = models.ClarityTimesheet(
        contractor_name="Jane Doe", contractor_name_normalized=normalize_name("Jane Doe"),
        hours=40.0, date_worked=date(2026, 5, 1), is_posted=True, is_time_off=False,
        project_id="PR999", investment_name="Generic Project (no name signal)", capex_opex="OPEX",
        source_row_hash="tsX",
    )
    db.add(ts); db.flush()
    inv = models.Invoice(
        vendor_name="AVASOFT", invoice_number="INV-200", status=models.STATUS_MATCHED,
        date_received=date(2026, 5, 31), total_invoice_cost=3800.0,
        line_items=[models.InvoiceLineItem(
            contractor_name="Jane Doe", contractor_name_normalized=normalize_name("Jane Doe"),
            hours=40.0, rate=95.0, amount=3800.0, line_status=models.STATUS_MATCHED,
            matched_clarity_id=ts.id, diff={"clarity_hours": 40.0},
        )],
    )
    db.add(inv); db.commit(); db.refresh(inv)
    line = dict(zip(INVOICE_LINE_COLUMNS, _parse(coupa_csv_bytes(inv, db))[3]))
    assert line["Account Segment 1"] == "67"      # ACIMA company code (by project id)
    assert line["Account Segment 2"] == "AC000"   # ACIMA cost center
    assert line["Account Segment 3"] == "667070"  # OPEX GL code


def _split_invoice(db: Session):
    """One contractor whose Clarity hours span a RAC project (30h) and an ACIMA project (40h)."""
    base = dict(
        contractor_name="Split Contractor",
        contractor_name_normalized=normalize_name("Split Contractor"),
        is_posted=True, is_time_off=False,
    )
    rac = models.ClarityTimesheet(
        **base, hours=30.0, date_worked=date(2026, 5, 2), project_id="PRAC",
        investment_name="Some RAC Project", capex_opex="CAPEX", source_row_hash="r1",
    )
    aci = models.ClarityTimesheet(
        **base, hours=40.0, date_worked=date(2026, 5, 3), project_id="PACI",
        investment_name="Some ACIMA Project", capex_opex="CAPEX", source_row_hash="a1",
    )
    db.add_all([rac, aci]); db.flush()
    inv = models.Invoice(
        vendor_name="AVASOFT", invoice_number="INV-300", status=models.STATUS_MATCHED,
        date_received=date(2026, 5, 31),
        payment_period_start=date(2026, 5, 1), payment_period_end=date(2026, 5, 31),
        line_items=[models.InvoiceLineItem(
            contractor_name="Split Contractor",
            contractor_name_normalized=normalize_name("Split Contractor"),
            hours=70.0, rate=100.0, amount=7000.0, line_status=models.STATUS_MATCHED,
            matched_clarity_id=rac.id, diff={"clarity_hours": 70.0},
        )],
    )
    db.add(inv); db.commit(); db.refresh(inv)
    return inv


def test_split_contractor_into_one_line_per_company(db: Session, monkeypatch):
    import app.services.coupa as coupa
    monkeypatch.setattr(coupa, "_project_company_map", lambda: {"PRAC": "RAC", "PACI": "ACIMA"})
    inv = _split_invoice(db)
    line_rows = [r for r in _parse(coupa_csv_bytes(inv, db))[2:] if r[0] == "Invoice Line"]
    assert len(line_rows) == 2  # one contractor -> two lines (RAC, ACIMA)
    by = {dict(zip(INVOICE_LINE_COLUMNS, r))["Account Segment 1"]: dict(zip(INVOICE_LINE_COLUMNS, r))
          for r in line_rows}
    rac, aci = by["5"], by["67"]
    # RAC line: 30 Clarity hours, RAC cost center; total = 30 x invoice rate 100 (Coupa computes it).
    assert rac["Quantity"] == "30" and rac["Account Segment 2"] == "H0003" and rac["Price*"] == "100.00"
    # ACIMA line: 40 hours, ACIMA cost center.
    assert aci["Quantity"] == "40" and aci["Account Segment 2"] == "AC000"
    # Line numbers are sequential across the split.
    assert {r[4] for r in line_rows} == {"1", "2"}


def test_single_company_contractor_stays_one_line(db: Session, monkeypatch):
    import app.services.coupa as coupa
    monkeypatch.setattr(coupa, "_project_company_map", lambda: {"PR999": "ACIMA"})
    inv = _matched_invoice(db)  # one contractor, one project PR1 (not in map) -> single bucket
    line_rows = [r for r in _parse(coupa_csv_bytes(inv, db))[2:] if r[0] == "Invoice Line"]
    assert len(line_rows) == 1
    assert dict(zip(INVOICE_LINE_COLUMNS, line_rows[0]))["Quantity"] == "40"  # invoice hours


def test_matched_invoice_gets_real_chart_of_accounts(db: Session):
    inv = _matched_invoice(db)  # status == matched
    assert build_header_row(inv)["Chart of Accounts*"] == "Chart of Accounts"


def test_flagged_invoice_leaves_chart_blank(db: Session):
    inv = _matched_invoice(db)
    inv.status = models.STATUS_FLAGGED
    assert build_header_row(inv)["Chart of Accounts*"] == ""


def test_draft_csv_includes_only_matched_contractors(db: Session):
    inv = _matched_invoice(db)            # one matched contractor (Jane Doe)
    inv.status = models.STATUS_FLAGGED    # but the invoice as a whole is flagged
    inv.line_items.append(models.InvoiceLineItem(
        contractor_name="Unmatched Person",
        contractor_name_normalized=normalize_name("Unmatched Person"),
        hours=10.0, rate=50.0, amount=500.0, line_status=models.STATUS_FLAGGED,
    ))
    db.commit()
    rows = _parse(coupa_csv_bytes(inv, db, matched_only=True))
    line_rows = [r for r in rows[2:] if r[0] == "Invoice Line"]
    descriptions = " ".join(r[5] for r in line_rows)
    assert "Jane Doe" in descriptions            # matched contractor IS included
    assert "Unmatched Person" not in descriptions  # unmatched contractor is OMITTED
    # Draft of a flagged invoice leaves the Chart of Accounts blank (not a clean match).
    header = dict(zip(INVOICE_HEADER_COLUMNS, rows[2]))
    assert header["Chart of Accounts*"] == ""


def test_draft_filename_is_prefixed(db: Session):
    inv = _matched_invoice(db)
    assert coupa_csv_filename(inv, draft=True) == "DRAFT_AVASOFT_INV-100.csv"


def test_unknown_fields_are_left_blank(db: Session):
    # We no longer emit placeholder tokens: fields we can't source are simply blank in the CSV.
    inv = _matched_invoice(db)
    header = dict(zip(INVOICE_HEADER_COLUMNS, _parse(coupa_csv_bytes(inv, db))[2]))
    assert header["Requester Email"] == ""
    assert header["Requester Name"] == ""
    assert header["PO Number"] == "" if "PO Number" in header else True  # no PO on the header
    assert header["Batch ID"] == ""


def test_approver_from_tracker_fills_requester_name(db: Session, monkeypatch):
    # The copy tracker maps (vendor, invoice number) -> approver; it lands in the Requester Name cell
    # (the sample's "<<Approver Name>>" placeholder).
    from app.services.coupa import approver_for

    approver_for.cache_clear()
    monkeypatch.setattr(
        coupa, "_approver_index",
        lambda: {"inv-100": [("avasoft", "Oscar Trelles")]},
    )
    inv = _matched_invoice(db)  # vendor AVASOFT, invoice INV-100
    header = dict(zip(INVOICE_HEADER_COLUMNS, _parse(coupa_csv_bytes(inv, db))[2]))
    assert header["Requester Name"] == "Oscar Trelles"
    assert header["Requester Email"] == ""  # only the name is sourced; email stays blank
    approver_for.cache_clear()


def test_approver_unambiguous_by_invoice_number(monkeypatch):
    from app.services.coupa import approver_for

    approver_for.cache_clear()
    # One invoice number, one approver -> resolved even if the vendor name doesn't match exactly.
    monkeypatch.setattr(coupa, "_approver_index", lambda: {"6347": [("advanced communications group", "Oscar Trelles")]})
    assert approver_for("Advanced Comms Group LLC", "6347") == "Oscar Trelles"
    assert approver_for("Anyone", 6347) == "Oscar Trelles"       # numeric invoice number too
    assert approver_for("Anyone", "ZZZ") is None                  # unknown number -> None
    approver_for.cache_clear()


def test_approver_disambiguated_by_vendor_when_number_shared(monkeypatch):
    from app.services.coupa import approver_for

    approver_for.cache_clear()
    # Same invoice number used by two vendors -> vendor picks the approver.
    monkeypatch.setattr(
        coupa, "_approver_index",
        lambda: {"2026-001": [("amandh solutions", "Juan Rajani"), ("other vendor", "Someone Else")]},
    )
    assert approver_for("Amandh Solutions", "2026-001") == "Juan Rajani"
    assert approver_for("Other Vendor", "2026-001") == "Someone Else"
    approver_for.cache_clear()


def test_tracking_accounting_lists_distinct_values(monkeypatch):
    from app.services.coupa import tracking_accounting_for

    tracking_accounting_for.cache_clear()
    # invoice 18874 splits across two cost centers, one offset GL -> distinct values, first-seen order.
    monkeypatch.setattr(
        coupa, "_tracker_accounting_index",
        lambda: {
            "18874": [("DT600", "679030"), ("99940", "679030")],
            "900000255559": [("DT800", "664070")],
        },
    )
    split = tracking_accounting_for("18874")
    assert split == {"cost_center": "DT600, 99940", "offset_gl_account": "679030"}
    single = tracking_accounting_for("900000255559")
    assert single == {"cost_center": "DT800", "offset_gl_account": "664070"}
    tracking_accounting_for.cache_clear()


def test_tracking_accounting_unknown_invoice_is_none(monkeypatch):
    from app.services.coupa import tracking_accounting_for

    tracking_accounting_for.cache_clear()
    monkeypatch.setattr(coupa, "_tracker_accounting_index", lambda: {})
    assert tracking_accounting_for("NOPE") == {"cost_center": None, "offset_gl_account": None}
    assert tracking_accounting_for(None) == {"cost_center": None, "offset_gl_account": None}
    tracking_accounting_for.cache_clear()


def test_load_supplier_index_normalizes_names(tmp_path):
    p = tmp_path / "suppliers.csv"
    p.write_text(
        "Name,Supplier Number\n"
        "AVASOFT INC-317598 (08820),RAC-317598\n"            # strip "-317598" and "(08820)"
        "GLOBAL COMPASS TECHNOLOGIES LLC (84043),RAC-363223\n"
        "NO NUMBER VENDOR (12345),\n",                        # blank number -> skipped
        encoding="utf-8",
    )
    exact, names, numbers, despaced = _load_supplier_index(p)
    assert exact["avasoft inc"] == "RAC-317598"
    assert exact["global compass technologies llc"] == "RAC-363223"
    assert "no number vendor" not in exact
    assert despaced["avasoft"] == {"RAC-317598"}  # core-name key


def test_supplier_number_lookup_exact_and_unknown(monkeypatch):
    supplier_number_for.cache_clear()
    monkeypatch.setattr(
        coupa, "_supplier_index",
        lambda: ({"acme inc": "RAC-9"}, ["acme inc"], ["RAC-9"], {"acme": {"RAC-9"}}),
    )
    assert supplier_number_for("ACME Inc.") == "RAC-9"          # punctuation-insensitive exact match
    assert supplier_number_for("Totally Different Co") is None  # no confident match -> None (placeholder)
    supplier_number_for.cache_clear()


def test_supplier_number_matches_despite_suffix_and_spacing(monkeypatch):
    # The CIGNITI case: invoice vendor parsed spaceless as "CIGNITITECHNOLOGIESLIMITED" must still match
    # the list's "Cigniti Technologies Inc" by unambiguous core name (suffix Limited vs Inc ignored).
    supplier_number_for.cache_clear()
    idx = ({"cigniti technologies inc": "RAC-281553"}, ["cigniti technologies inc"],
           ["RAC-281553"], {"cignititechnologies": {"RAC-281553"}})
    monkeypatch.setattr(coupa, "_supplier_index", lambda: idx)
    assert supplier_number_for("CIGNITITECHNOLOGIESLIMITED") == "RAC-281553"
    supplier_number_for.cache_clear()


def test_supplier_number_ambiguous_core_name_not_guessed(monkeypatch):
    # Two suppliers share a core name -> don't guess (return None / placeholder) unless one is exact.
    supplier_number_for.cache_clear()
    idx = ({"avasoft": "RAC-298764", "avasoft inc": "RAC-317598"},
           ["avasoft", "avasoft inc"], ["RAC-298764", "RAC-317598"],
           {"avasoft": {"RAC-298764", "RAC-317598"}})
    monkeypatch.setattr(coupa, "_supplier_index", lambda: idx)
    assert supplier_number_for("AVASOFT Inc.") == "RAC-317598"   # exact still resolves
    assert supplier_number_for("Avasoft Holdings") is None       # ambiguous core -> not guessed
    supplier_number_for.cache_clear()


def test_header_supplier_number_filled_from_list(db: Session, monkeypatch):
    supplier_number_for.cache_clear()
    monkeypatch.setattr(
        coupa, "_supplier_index",
        lambda: ({"avasoft": "RAC-555"}, ["avasoft"], ["RAC-555"], {"avasoft": {"RAC-555"}}),
    )
    inv = _matched_invoice(db)  # vendor "AVASOFT"
    assert build_header_row(inv)["Supplier Number"] == "RAC-555"
    supplier_number_for.cache_clear()


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
