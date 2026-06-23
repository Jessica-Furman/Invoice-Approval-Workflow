"""Tests for invoice parsing (M3).

Number-cleaning is pure-unit. The sample-PDF tests run only when the sample files are present
(they live in the repo's contractor_invoices/ folder).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.parsing import parse_invoice
from app.services.parsing.rules import (
    clean_number,
    extract_person_name,
    parse_services_rendered,
    _month_of_period,
)


def test_parse_services_rendered_multi_contractor():
    # Gravity IT format: pdfplumber crams several "Services Rendered for:" contractors into one row
    # as newline-joined cells. Each must be split out into its own line item.
    table = [
        ["Date Ending", "Description", "Quantity", "Rate", "Amount"],
        [
            "06/05/2026\n06/05/2026\n06/05/2026",
            "Services Rendered for: Amruthaj, Peter - Product\nManager\nPO Number:\n"
            "Services Rendered for: Huffaker, Ben - Product Owner\nPO Number:\n"
            "Services Rendered for: Osei, Prince - Mobile\nDevelopment Team Lead\nPO Number:",
            "40\n40\n40",
            "$95.00\n$88.00\n$120.00",
            "$3,800.00\n$3,520.00\n$4,800.00",
        ],
    ]
    items = parse_services_rendered([table])
    assert [li.contractor_name for li in items] == ["Amruthaj Peter", "Huffaker Ben", "Osei Prince"]
    assert [li.hours for li in items] == [40.0, 40.0, 40.0]
    assert [li.rate for li in items] == [95.0, 88.0, 120.0]
    assert items[2].amount == 4800.0


def test_invoice_for_the_month_of_period():
    # "Invoice for the month of <Month> <Year>" -> the full calendar month, even with no spaces
    # (pdfplumber concatenates words on some vendor PDFs, e.g. Coforge).
    assert _month_of_period("Invoice for the month of April 2026") == "4/1/2026 - 4/30/2026"
    assert _month_of_period("InvoiceforthemonthofApril2026") == "4/1/2026 - 4/30/2026"
    assert _month_of_period("for the month of Dec 2025") == "12/1/2025 - 12/31/2025"
    assert _month_of_period("for the month of February 2026") == "2/1/2026 - 2/28/2026"
    assert _month_of_period("no period phrasing here") is None

SAMPLES = Path(__file__).resolve().parents[2] / "contractor_invoices"


def test_extract_person_name_from_descriptions():
    # Name buried in a longer description line — pull out just the human name.
    assert extract_person_name("IT consultancy and development services (Przemek Szyszka)") == "Przemek Szyszka"
    assert extract_person_name("Software development services - John Smith") == "John Smith"
    assert extract_person_name("Consulting services provided by Maria Lopez") == "Maria Lopez"
    assert extract_person_name("Contractor: David Chen") == "David Chen"
    assert extract_person_name("Professional services for Jane Miller, May 2026") == "Jane Miller"
    # Parentheses win, across a line break, with diacritics.
    assert extract_person_name("IT consultancy and development\nservices (Paweł Cyło)") == "Paweł Cyło"
    assert extract_person_name("Quality Assurance Service\n(Sebastian Wcisło)") == "Sebastian Wcisło"
    # Already-clean names (incl. middle initial, 4-token, nobiliary particle) pass through unchanged.
    assert extract_person_name("Noorul Sarfaraz 04/26/2026 - 05/30/2026") == "Noorul Sarfaraz"
    assert extract_person_name("Sachin R Gangolli") == "Sachin R Gangolli"
    assert extract_person_name("Durga Rupa Sree Tamarala") == "Durga Rupa Sree Tamarala"
    assert extract_person_name("Maria de Souza") == "Maria de Souza"
    # No human name present → None (caller flags for review).
    assert extract_person_name("Professional services rendered") is None
    assert extract_person_name("IT consultancy and development services") is None
    assert extract_person_name("") is None


def test_extract_person_name_after_project_and_dates():
    # AVASOFT/Coforge shape: project label + date range first, contractor name after, role last.
    assert (
        extract_person_name("Mobile App Development - 01-Apr to 30-Apr 2026 -\nSharan Manivannan - Lead")
        == "Sharan Manivannan"
    )
    assert (
        extract_person_name("Mobile App Development - 01-Apr to 30-Apr 2026 -\nBibin Roy Lead")
        == "Bibin Roy"
    )
    assert (
        extract_person_name(
            "Mobile App Development - 01-Apr to 30-Apr 2026 -\nDhinakaran Gnana Sambandam - Developer"
        )
        == "Dhinakaran Gnana Sambandam"
    )
    # Name still found when it comes BEFORE the date (must not regress).
    assert extract_person_name("Noorul Sarfaraz 04/26/2026 - 05/30/2026") == "Noorul Sarfaraz"


def test_clean_number_recovers_mangled_values():
    assert clean_number("$2,400") == 2400.0
    assert clean_number("8 3.00") == 83.0           # CIGNITI rate split by stray space
    assert clean_number("1 5,936.00") == 15936.0    # CIGNITI amount split by stray space
    assert clean_number("180 Hrs") == 180.0         # TCS units cell
    assert clean_number("90 400,00") == 90400.0      # Ironin EU: space=thousands, comma=decimal
    assert clean_number("90 400,00 USD") == 90400.0
    assert clean_number("1.234,56") == 1234.56       # EU: dot=thousands, comma=decimal
    assert clean_number("0,00") == 0.0
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


def test_parse_from_ocr_text_blocks():
    """OCR returns each table cell on its own line; the block parser reconstructs line items."""
    import textwrap

    from app.services.parsing.rules import parse_from_text

    ocr_text = textwrap.dedent(
        """\
        INVOICE
        Healy Consulting LLC
        Invoice Number
        INV-0137
        Contact: Joe Healy
        Description
        Quantity
        Unit Price
        Amount USD
        4/27/26-5/3/26-Unified Customer Profile Project
        40.00
        175.00
        7,000.00
        5/4/26-5/10/26-Unified Customer Profile Project
        32.00
        175.00
        5,600.00
        TOTAL USD
        12,600.00
        """
    )
    r = parse_from_text(ocr_text)
    p = r.parsed
    assert p.vendor_name == "Healy Consulting LLC"
    assert p.invoice_number == "INV-0137"
    assert p.contractor_name == "Joe Healy"
    assert len(p.line_items) == 2
    assert p.line_items[0].hours == 40.0 and p.line_items[0].rate == 175.0
    assert p.total_invoice_cost == 12600.0
