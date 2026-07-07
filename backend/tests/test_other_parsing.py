"""Tests for the "Other Invoice Types" parser (hardware/software/subscription).

Unit tests are pure. The sample-PDF tests run only when the example invoices are present under
documentation/Hardware_and_software_invoices/.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas import ParsedOtherInvoice, ParsedOtherLineItem
from app.services.parsing.other_rules import (
    _extract_total,
    _line_items_from_text,
    _parse_other_table,
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
