"""Tests for the "Other Invoice Types" parser (hardware/software/subscription).

Unit tests are pure. The sample-PDF tests run only when the example invoices are present under
documentation/Hardware_and_software_invoices/.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas import ParsedOtherInvoice, ParsedOtherLineItem
from app.services.parsing.other_rules import (
    _choose_line_items,
    _email_domain_vendors,
    _extract_total,
    _line_items_from_tables,
    _line_items_from_text,
    _line_items_from_words,
    _parse_other_table,
    _segment_row,
    parse_other_invoice,
    required_missing_fields,
)

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "documentation" / "Hardware_and_software_invoices"
SUPPLIER_CSV = Path(__file__).resolve().parents[2] / "documentation" / "Active supplier list.csv"


# --- missing-data logic (quantity & unit price are optional) ---------------------------------
def _full(**over) -> ParsedOtherInvoice:
    base = dict(
        vendor_name="GitHub, Inc",
        invoice_number="INV1",
        total_invoice_cost=100.0,
        line_items=[ParsedOtherLineItem(description="Copilot", amount=100.0)],
    )
    base.update(over)
    from datetime import date
    base.setdefault("date_received", date(2026, 6, 1))
    return ParsedOtherInvoice(**base)


def test_all_present_with_supplier_is_not_missing():
    assert required_missing_fields(_full(), "RAC-9") == []


def test_qty_and_unit_price_are_optional():
    # No quantity/unit price on the line -> still complete.
    p = _full(line_items=[ParsedOtherLineItem(description="Subscription", amount=100.0)])
    assert required_missing_fields(p, "RAC-9") == []


def test_unresolved_supplier_is_missing():
    assert "supplier number" in required_missing_fields(_full(), None)


def test_missing_total_and_description_flagged():
    p = _full(total_invoice_cost=None, line_items=[])
    miss = required_missing_fields(p, "RAC-9")
    assert "total price" in miss and "service description" in miss


# --- invoice grand total (entire invoice, not a line item or a partial payment) --------------
def test_total_prefers_full_invoice_total_over_balance_and_paid():
    # Very Good Security shape: full Total wins over "Total Paid" (a payment) and "Balance Due".
    text = (
        "Subtotal: USD 6,250.00\n"
        "Total: USD 6,715.63\n"
        "Total Paid: USD 2,655.90\n"
        "Balance Due: USD 4,059.73\n"
    )
    assert _extract_total(text) == 6715.63


def test_total_uses_invoice_total_label_first():
    assert _extract_total("Invoice Total: $50.00\nBalance Due: $30.00") == 50.0


def test_total_falls_back_to_balance_due_when_no_total_printed():
    assert _extract_total("Amount Due $123.45") == 123.45


def test_total_is_none_when_nothing_printed():
    # Nothing labeled -> None, so the caller sums the line items instead.
    assert _extract_total("Widget shipment for the month of May") is None


def test_missing_total_is_summed_from_line_items():
    # When no total is printed, parse fills it from the sum of line amounts (see parse_other_invoice).
    from app.services.parsing.other_rules import _line_items_from_tables

    tables = [[["Description", "Amount"], ["Item A", "40.00"], ["Item B", "60.00"]]]
    items = _line_items_from_tables(tables)
    assert round(sum(li.amount for li in items), 2) == 100.0


# --- table tier -------------------------------------------------------------------------------
def test_table_parser_maps_columns_and_skips_footer():
    table = [
        ["Description", "Qty", "Rate", "Amount"],
        ["Managed service", "2", "10.00", "20.00"],
        ["Total", "", "", "100.00"],  # footer must be skipped
    ]
    items = _parse_other_table(table)
    assert len(items) == 1
    assert items[0].description == "Managed service"
    assert items[0].quantity == 2 and items[0].unit_price == 10.0 and items[0].amount == 20.0


def test_summary_table_beats_bigger_detail_appendix():
    # CyrusOne case: the billing-summary table has 1 row with a real "Description" column; a per-ticket
    # appendix has MORE rows but only a weaker "Service Type" column. The summary must win.
    summary = [
        ["QTY", "LOCATION", "ITEM NUMBER", "SERVICE PERIOD", "DESCRIPTION", "CHARGE", "TAX", "TOTAL"],
        ["0.00", "2501 South State Hwy", "CON201-N", "04/01 - 04/30", "Smarthands - OP", "$75.00", "$0.00", "$75.00"],
    ]
    appendix = [
        ["Ticket ID", "Date Solved", "Service Type", "Requester", "Billable Hours", "Rate", "Charge Amount"],
        ["3442377", "04-01-2026", "Shipping::Accept & Notify", "Clinton Snow", "0.25", "100.00", "$25.00"],
        ["3460182", "04-15-2026", "Shipping::Accept & Notify", "Clinton Snow", "0.25", "100.00", "$25.00"],
        ["3463453", "04-17-2026", "Shipping::Accept & Notify", "Clinton Snow", "0.25", "100.00", "$25.00"],
    ]
    # Appendix listed first and has 3x the rows, but the summary table still wins on desc-column strength.
    items = _line_items_from_tables([appendix, summary])
    assert len(items) == 1
    assert items[0].description == "Smarthands - OP" and items[0].amount == 75.0


def test_table_parser_prefers_service_description_over_item_code():
    table = [
        ["Item", "Service Description", "Amount"],
        ["ZC-900", "Google Maps Platform usage", "61,224.55"],
    ]
    items = _parse_other_table(table)
    assert items[0].description == "Google Maps Platform usage"
    assert items[0].amount == 61224.55


# --- text tier (GitHub-style vertical layout) ------------------------------------------------
def test_text_fallback_pairs_description_with_amount():
    text = (
        "DESCRIPTION AMOUNT NET AMOUNT\n"
        "GitHub Actions Usage\n"
        "$469.26 $469.26\n"
        "May 01, 2026 - May 31, 2026\n"
        "GitHub Copilot Usage\n"
        "$4,266.04 $4,266.04\n"
        "May 01, 2026 - May 31, 2026\n"
        "SUBTOTAL: $4,735.31\n"
        "INVOICE TOTAL: $4,735.31\n"
    )
    items = _line_items_from_text(text)
    descs = [i.description for i in items]
    assert "GitHub Actions Usage" in descs and "GitHub Copilot Usage" in descs
    assert {i.amount for i in items} == {469.26, 4266.04}  # totals/subtotal excluded


# --- vendor from email domain (billing-shell letterhead) -------------------------------------
def test_email_domain_vendor_candidates_case_and_skips_banks():
    text = (
        "C1 Ground Tenant LLC\n"
        "PNC Bank\n"
        "Direct questions to accountsreceivable@cyrusone.com or invoicing@cyrusone.com\n"
        "footer brand CyrusOne * Dallas, TX\n"
    )
    cands = _email_domain_vendors(text)
    assert "CyrusOne" in cands          # cased from the text occurrence, not "cyrusone"
    assert all("pnc" not in c.lower() for c in cands)  # remit bank domain skipped


@pytest.mark.skipif(
    not (SAMPLE_DIR / "CyrusOne_900000255559-2026-05-28_07-39-43.pdf").exists() or not SUPPLIER_CSV.exists(),
    reason="CyrusOne sample or supplier list absent",
)
def test_cyrusone_uses_brand_not_billing_shell():
    # The text letterhead is the billing shell "C1 Ground Tenant LLC" (not a supplier); the parser
    # must fall back to the email-domain brand "CyrusOne", which IS in the supplier list.
    from app.services.coupa import supplier_number_for

    r = parse_other_invoice(str(SAMPLE_DIR / "CyrusOne_900000255559-2026-05-28_07-39-43.pdf"))
    assert r.parsed.vendor_name == "CyrusOne"
    assert "C1 Ground Tenant" not in (r.parsed.vendor_name or "")
    assert supplier_number_for(r.parsed.vendor_name) is not None


# --- word-position tier (generic multi-column reconstruction, e.g. Salesforce) ----------------
def _w(text: str, x0: float, top: float, cw: float = 6.0) -> dict:
    return {"text": text, "x0": x0, "x1": x0 + len(text) * cw, "top": top}


def _row(tokens: list[tuple[str, float]], top: float) -> list[dict]:
    return [_w(t, x0, top) for t, x0 in tokens]


def test_segment_row_splits_columns_not_words():
    # "Additional Orders - B2B" (small spaces) stays one cell; the wide gap before the number splits.
    words = _row([("Additional", 40), ("Orders", 105), ("-", 150), ("B2B", 160), ("203,742.00", 300)], top=10)
    cells = _segment_row(words)
    assert cells == ["Additional Orders - B2B", "203,742.00"]


def test_words_tier_reconstructs_salesforce_like_columns():
    # Header: Service | Quote # | Months | Qty | Unit Price | Tax Rate | Tax | Total (8 columns).
    header = _row([("Service", 40), ("Quote", 280), ("#", 318), ("Months", 400), ("Qty", 480),
                   ("Unit", 560), ("Price", 590), ("Tax", 660), ("Rate", 690), ("Tax", 760), ("Total", 840)], top=10)
    row1 = _row([("1", 40), ("Additional", 52), ("Orders", 120), ("-", 165), ("B2B", 175),
                 ("Q-08781791", 280), ("12.00", 400), ("38,500", 480), ("0.44", 560), ("0%", 660),
                 ("0.00", 760), ("203,742.00", 840)], top=30)
    wrap = _row([("Commerce", 52), ("-", 108), ("LP", 120)], top=45)
    row2 = _row([("2", 40), ("B2B", 52), ("Commerce", 76), ("Platform", 130),
                 ("Q-08781791", 280), ("12.00", 400), ("1", 480), ("3,600.00", 560), ("0%", 660),
                 ("0.00", 760), ("43,200.00", 840)], top=60)
    items = _line_items_from_words([header + row1 + wrap + row2])
    assert len(items) == 2
    assert items[0].amount == 203742.0 and items[0].quantity == 38500.0 and items[0].unit_price == 0.44
    assert "Additional Orders - B2B" in items[0].description
    assert "Commerce" in items[0].description  # the wrapped line was appended
    assert items[1].amount == 43200.0 and items[1].quantity == 1.0


def test_choose_line_items_prefers_sum_closest_to_total():
    from app.schemas import ParsedOtherLineItem as LI

    collapsed = [LI(description="one big row", amount=203742.0)]          # a collapsed table
    full = [LI(description="a", amount=203742.0), LI(description="b", amount=43200.0)]  # the word tier
    items, label = _choose_line_items([("rules", collapsed), ("words", full)], total=246942.0)
    assert label == "words" and len(items) == 2


def test_choose_line_items_splits_collapsed_blob_on_equal_sum():
    from app.schemas import ParsedOtherLineItem as LI

    blob = [LI(description="x y", amount=100.0)]                          # a collapsed single row
    split = [LI(description="x", amount=60.0), LI(description="y", amount=40.0)]
    # Both sum to the total (100); prefer the set that splits the blob into its real rows.
    items, label = _choose_line_items([("rules", blob), ("words", split)], total=100.0)
    assert label == "words" and len(items) == 2


_SALESFORCE_PDF = (
    Path(__file__).resolve().parents[2] / "data" / "storage" / "AMER_Invoice_38201424_21-06-2026_001011.pdf"
)


@pytest.mark.skipif(not _SALESFORCE_PDF.exists(), reason="Salesforce sample not present")
def test_salesforce_parses_clean_line_items_end_to_end():
    r = parse_other_invoice(str(_SALESFORCE_PDF))
    p = r.parsed
    assert p.vendor_name and "salesforce" in p.vendor_name.lower()
    assert p.total_invoice_cost == 246942.0
    # The generic word tier recovers real service lines (not the collapsed "1 Additional Orders..." blob).
    assert len(p.line_items) >= 2
    assert any((li.quantity or 0) > 0 for li in p.line_items)          # quantity parsed (was 0 before)
    assert abs(sum(li.amount or 0 for li in p.line_items) - 246942.0) < 1.0  # lines sum to the total


# --- sample PDFs --------------------------------------------------------------------------------
_SAMPLES = sorted(SAMPLE_DIR.glob("*.pdf")) if SAMPLE_DIR.exists() else []


@pytest.mark.skipif(not _SAMPLES, reason="sample invoices not present")
@pytest.mark.parametrize("pdf", _SAMPLES, ids=lambda p: p.name[:24])
def test_every_sample_yields_total_and_invoice_number(pdf: Path):
    r = parse_other_invoice(str(pdf))
    assert r.parsed.total_invoice_cost is not None, f"no total parsed for {pdf.name}"
    assert r.parsed.invoice_number, f"no invoice number for {pdf.name}"


@pytest.mark.skipif(not (SAMPLE_DIR / "GitHub_INV138442106.pdf").exists(), reason="GitHub sample absent")
def test_github_sample_structure():
    r = parse_other_invoice(str(SAMPLE_DIR / "GitHub_INV138442106.pdf"))
    p = r.parsed
    assert p.invoice_number == "INV138442106"
    assert p.total_invoice_cost == 4735.31
    assert len(p.line_items) == 3
    assert any("GitHub" in (li.description or "") for li in p.line_items)


@pytest.mark.skipif(
    not (SAMPLE_DIR / "GitHub_INV138442106.pdf").exists() or not SUPPLIER_CSV.exists(),
    reason="sample or supplier list absent",
)
def test_github_resolves_supplier_and_has_no_missing_fields():
    from app.services.coupa import supplier_number_for

    r = parse_other_invoice(str(SAMPLE_DIR / "GitHub_INV138442106.pdf"))
    sup = supplier_number_for(r.parsed.vendor_name)
    assert sup is not None
    assert required_missing_fields(r.parsed, sup) == []
