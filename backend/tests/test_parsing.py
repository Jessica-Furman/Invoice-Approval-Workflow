"""Tests for invoice parsing (M3).

Number-cleaning is pure-unit. The sample-PDF tests run only when the sample files are present
(they live in the repo's contractor_invoices/ folder).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.parsing import parse_invoice
from app.services.parsing.rules import clean_number

SAMPLES = Path(__file__).resolve().parents[2] / "contractor_invoices"


def test_clean_number_recovers_mangled_values():
    assert clean_number("$2,400") == 2400.0
    assert clean_number("8 3.00") == 83.0           # CIGNITI rate split by stray space
    assert clean_number("1 5,936.00") == 15936.0    # CIGNITI amount split by stray space
    assert clean_number("180 Hrs") == 180.0         # TCS units cell
    assert clean_number("") is None
    assert clean_number(None) is None


@pytest.mark.skipif(not (SAMPLES / "invoice1.pdf").exists(), reason="sample PDFs not present")
def test_avasoft_invoice_fields():
    out = parse_invoice(str(SAMPLES / "invoice1.pdf"))
    p = out.parsed
    assert p.vendor_name and "AVASOFT" in p.vendor_name
    assert p.invoice_number == "REN0609202621882"
    assert str(p.date_received) == "2026-06-01"
    assert p.total_invoice_cost == 30400.0
    assert len(p.line_items) == 7
    first = p.line_items[0]
    assert first.contractor_name == "Noorul Sarfaraz"
    assert first.hours == 80.0 and first.rate == 30.0 and first.amount == 2400.0


@pytest.mark.skipif(not (SAMPLES / "invoice2.pdf").exists(), reason="sample PDFs not present")
def test_cigniti_recovers_46_line_items_with_clean_numbers():
    out = parse_invoice(str(SAMPLES / "invoice2.pdf"))
    p = out.parsed
    assert p.invoice_number == "F20610005297"
    assert p.total_invoice_cost == 349410.0
    assert len(p.line_items) == 46
    rajesh = p.line_items[0]
    assert rajesh.contractor_name == "Rajesh Nimmala"
    assert rajesh.rate == 83.0 and rajesh.amount == 15936.0


@pytest.mark.skipif(not (SAMPLES / "invoice3.pdf").exists(), reason="sample PDFs not present")
def test_scanned_invoice_flags_for_vision():
    out = parse_invoice(str(SAMPLES / "invoice3.pdf"))
    assert out.has_text is False
    assert out.confidence == 0.0
    assert set(out.missing_required()) == {
        "vendor_name", "invoice_number", "date_received", "total_invoice_cost"
    }
