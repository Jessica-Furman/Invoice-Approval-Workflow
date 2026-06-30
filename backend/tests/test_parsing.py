"""Tests for invoice parsing (M3).

Number-cleaning is pure-unit. The sample-PDF tests run only when the sample files are present
(they live in the repo's contractor_invoices/ folder).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.parsing import parse_invoice
from app.schemas import ParsedLineItem
from app.services.ingestion import _invoice_no_from_filename
from app.services.parsing.rules import (
    clean_number,
    extract_person_name,
    parse_billable_lines,
    parse_cognizant_lines,
    parse_desc_qty_rate_amount,
    parse_global_compass,
    parse_qty_item_lines,
    parse_services_rendered,
    repair_mojibake_names,
    _billed_from_to_period,
    _clean_vendor,
    _header_month_period,
    _month_of_period,
)


def test_parse_qty_item_lines_odyssey():
    # Odyssey: "Qty Item Rate Amount" header then a plain-text data row "<hours> <name> $rate $amount".
    text = (
        "Bill To Rent A Center\n"
        "Qty Item Rate Amount\n"
        "176 Shanda Wright $93.00 $16,368.00\n"
        "Subtotal $16,368.00\n"
        "Tax (0%) $0.00\n"
        "Total $16,368.00\n"
        "1 of 1\n"
        "61805"
    )
    items = parse_qty_item_lines(text)
    assert len(items) == 1  # footer lines (Subtotal/Tax/Total) and "1 of 1" must NOT match
    assert items[0].contractor_name == "Shanda Wright"
    assert items[0].hours == 176.0
    assert items[0].rate == 93.0
    assert items[0].amount == 16368.0


def test_parse_desc_qty_rate_amount_nextstep():
    # NextStep Recruiting: "DESCRIPTION QTY RATE AMOUNT" text rows. DESCRIPTION = name-role-type (period);
    # QTY = hours, RATE = rate, AMOUNT = line total. Footer/bank-detail lines must NOT become line items.
    text = (
        "NextStep Recruiting LLC\n"
        "BILL TO INVOICE 260617056\n"
        "DESCRIPTION QTY RATE AMOUNT\n"
        "Stephen Dickison-Scrum Master-Reg Hours (5/31/26-6/6/26) 34 95.00 3,230.00\n"
        "Stephen Dickison-Scrum Master-Reg Hours (6/7/26-6/13/26) 40 95.00 3,800.00\n"
        "ACH Payment Information BALANCE DUE $7,030.00\n"
        "Routing Number: 111000753\n"
        "Account Number: 1881843815\n"
    )
    items = parse_desc_qty_rate_amount(text)
    assert len(items) == 2  # only the two contractor rows; BALANCE DUE / bank lines excluded
    assert [li.contractor_name for li in items] == ["Stephen Dickison", "Stephen Dickison"]
    assert [li.hours for li in items] == [34.0, 40.0]
    assert [li.rate for li in items] == [95.0, 95.0]
    assert [li.amount for li in items] == [3230.0, 3800.0]
    # Each line carries its own worked period (so the invoice's full span is recoverable).
    assert items[0].extra == {"period_start": "2026-05-31", "period_end": "2026-06-06"}
    assert items[1].extra == {"period_start": "2026-06-07", "period_end": "2026-06-13"}


def test_desc_qty_parser_requires_header():
    # Without the DESCRIPTION/QTY/AMOUNT header the loose row pattern must not fire.
    text = "Stephen Dickison-Scrum Master (5/31/26-6/6/26) 34 95.00 3,230.00\n"
    assert parse_desc_qty_rate_amount(text) == []


def test_parse_qty_item_lines_requires_header():
    # Without a "Qty … Item" header, don't guess line items from arbitrary "<n> <word> $ $" lines.
    assert parse_qty_item_lines("176 Shanda Wright $93.00 $16,368.00") == []


def test_parse_billable_lines_sogeti():
    # Sogeti/Capgemini text layout: "<#> <Last, First> ...Billable <hours> Hours @ <rate>".
    # Covers a wrapped rate (group None) and a page-break-truncated last row.
    text = (
        "Item Description Tax Unit PriceExtended Amount\n"
        "1 Akde, Sridevi ...Billable 189.00 Hours @ 20.00 No 3,780.00 3,780.00\n"
        "2 Deshmukh, Pravin Diwakar ...Billable 180.00 Hours @ 30.00No 5,400.00 5,400.00\n"
        "5 Khan, Mohd Alam Abdul Salam ...Billable 180.00 Hours @ No 4,500.00\n"
        "25.00\n"
        "13 Tiwari, Vinayak ...Billable 153.0"
    )
    items = parse_billable_lines(text)
    assert [li.contractor_name for li in items] == [
        "Akde, Sridevi",
        "Deshmukh, Pravin Diwakar",
        "Khan, Mohd Alam Abdul Salam",
        "Tiwari, Vinayak",
    ]
    assert [li.hours for li in items] == [189.0, 180.0, 180.0, 153.0]
    assert items[0].rate == 20.0
    assert items[2].rate is None  # wrapped onto the next line — still captured the name + hours


def test_billed_from_to_period():
    # Two-column layout pushes the dates behind other text; still parse the labeled range.
    text = "Account # 700603496 Billed From Date Billed To Date\nAccount Name: Sogeti USA 02-Mar-2026 31-Mar-2026"
    assert _billed_from_to_period(text) == "02-Mar-2026 - 31-Mar-2026"


def test_header_month_period():
    # A bare "Month YYYY" in the title/header (no "Period:" label) -> that full calendar month.
    assert (
        _header_month_period("Acima Mobile App Timesheet - April 2026\nName Sharan ...")
        == "4/1/2026 - 4/30/2026"
    )
    assert _header_month_period("Timesheet\nFebruary 2026\nName ...") == "2/1/2026 - 2/28/2026"
    # Per-line day-dates (2-digit year) must NOT be mistaken for a period.
    assert _header_month_period("Invoice 123\nDate Day\n1-Apr-26 8\n2-Apr-26 8") is None
    # A month only deep in the body (not the header) is ignored.
    assert _header_month_period("\n".join(["line"] * 10 + ["Worked in May 2026"])) is None


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


def test_parse_cognizant_lines():
    # Cognizant text rows: "<Name(Last,First)> <Location> <TimeType> <hours> <UOM> <rate> <amount>".
    # The accented name arrives mojibaked from the text layer (é -> U+FFFD); repaired separately.
    text = (
        "Name Efforts UOM Rate Net Billing\n"
        "Services rendered for Rent-A--Scrum Master-MAY 2026\n"
        "P�rez de la Cruz,Gerardo Onsite RTIME 144.00 MHR 70.00 10,080.00\n"
        "Smith,John Offshore RTIME 160.00 MHR 55.00 8,800.00\n"
        "Total Amount Due: 10,080.00 USD\n"
    )
    items = parse_cognizant_lines(text)
    assert len(items) == 2  # the "Total Amount Due" line (UOM 'USD') must NOT match
    first = items[0]
    assert first.contractor_name == "P�rez de la Cruz,Gerardo"  # location/time-type stripped
    assert first.hours == 144.0 and first.rate == 70.0 and first.amount == 10080.0
    assert items[1].contractor_name == "Smith,John" and items[1].hours == 160.0


def test_repair_mojibake_names_uses_ocr():
    # OCR reads accents the text layer mangled — fuzzy-match the mojibake name to the clean OCR line.
    items = [ParsedLineItem(contractor_name="P�rez de la Cruz,Gerardo", hours=144.0)]
    ocr_text = "Some header\nPérez de la Cruz,Gerardo\n144.00\nTotal Amount Due:\n"
    repair_mojibake_names(items, ocr_text)
    assert items[0].contractor_name == "Pérez de la Cruz,Gerardo"


def test_repair_mojibake_names_noop_without_replacement_char():
    # Clean names are left untouched (no OCR substitution).
    items = [ParsedLineItem(contractor_name="John Smith", hours=10.0)]
    repair_mojibake_names(items, "Jon Smithe\nJohn Smithers")
    assert items[0].contractor_name == "John Smith"


def test_parse_global_compass_captures_period_per_line():
    # pdfplumber jumbles Global Compass column order per row: period+hours then name+amount on one row,
    # everything on one line on another, and the dash before the rate is inconsistent (or absent).
    text = (
        "Global Compass Technologies, LLC\n"
        "PAY PERIOD BILLABLE DESCRIPTION TOTAL\n"
        "March 1-15, 2026 80 hours\n"
        "Hours- Crisitan Vargas- $65/hr $5,200.00\n"
        "March 1-15, 2026 Hours- David Auza $65/hr 80 hours $5,200.00\n"  # no dash before $
        "March 1-15, 2026 Hours- Emilio Garza - $75/hr 80 hours $6,000.00\n"  # spaced dash
        "March 1-15, 2026 Hours- Javier Olivares- $64/hr 73 hours $4,672.00\n"  # partial hours
        "TOTAL DUE $21,072.00\n"
    )
    items = parse_global_compass(text)
    assert [li.contractor_name for li in items] == [
        "Crisitan Vargas", "David Auza", "Emilio Garza", "Javier Olivares",
    ]
    assert [li.rate for li in items] == [65.0, 65.0, 75.0, 64.0]  # name/rate stay aligned
    # The "David Auza" row (no dash) is NOT dropped, and hours/amount don't desync.
    david = items[1]
    assert david.hours == 80.0 and david.amount == 5200.0
    assert items[3].hours == 73.0  # Javier's partial hours
    # Every line carries the pay period from its PAY PERIOD column.
    for li in items:
        assert li.extra["period_start"] == "2026-03-01"
        assert li.extra["period_end"] == "2026-03-15"
    # "TOTAL DUE" is not parsed as a contractor.
    assert all("total" not in (li.contractor_name or "").lower() for li in items)


def test_parse_global_compass_orphaned_year():
    # On some GC invoices the period's year is split onto its own line ("May 25- June 7," ... "2026"),
    # so it isn't adjacent. The parser must still resolve it (falling back to the document year).
    text = (
        "Global Compass Technologies, LLC\n"
        "INVOICE 1081 JUNE 12, 2026\n"
        "PAY PERIOD BILLABLE DESCRIPTION TOTAL\n"
        "May 25- June 7, 64 hours\n"
        "Hours- Crisitan Vargas- $65/hr $4,160.00\n"
        "2026\n"
        "May 25- June 7,\n"
        "Hours- David Tello- $70/hr 80 hours $5,600.00\n"
        "2026\n"
        "TOTAL DUE $9,760.00\n"
    )
    items = parse_global_compass(text)
    assert [li.contractor_name for li in items] == ["Crisitan Vargas", "David Tello"]
    assert items[0].hours == 64.0 and items[1].hours == 80.0
    for li in items:
        assert li.extra["period_start"] == "2026-05-25"
        assert li.extra["period_end"] == "2026-06-07"


def test_date_pattern_ignores_zip_code():
    from app.services.parsing.rules import extract_header

    # "Saratoga Springs, Utah 84045" must NOT be read as a date; the real date is the all-caps month.
    text = "Global Compass Technologies, LLC\nSaratoga Springs, Utah 84045\nINVOICE 1081 JUNE 12, 2026\n"
    assert str(extract_header(text)["date_received"]) == "2026-06-12"


def test_parse_global_compass_cross_month_period():
    text = (
        "Global Compass Technologies, LLC\n"
        "May 25 - June 7, 2026 Hours- Marcos Yu- $80/hr 80 hours $6,400.00\n"
        "TOTAL DUE $6,400.00\n"
    )
    items = parse_global_compass(text)
    assert len(items) == 1
    assert items[0].extra["period_start"] == "2026-05-25"
    assert items[0].extra["period_end"] == "2026-06-07"


def test_clean_vendor_strips_trailing_date_descriptors():
    assert _clean_vendor("Acima Mobile App Timesheet - April 2026") == "Acima Mobile App Timesheet"
    assert _clean_vendor("Odyssey Information Services, Inc. 4/30/2026") == "Odyssey Information Services, Inc."
    assert _clean_vendor("Cognizant Worldwide Limited 31-MAY-2026") == "Cognizant Worldwide Limited"
    # No trailing date -> unchanged.
    assert _clean_vendor("AVASOFT Inc.") == "AVASOFT Inc."
    assert _clean_vendor(None) is None


def test_invoice_no_from_filename():
    # Timesheets with no printed invoice number fall back to the leading code in the filename.
    assert _invoice_no_from_filename("ACI0501202621760_Invoice - Acima Mobile App April 2026") == "ACI0501202621760"
    assert _invoice_no_from_filename("AVASOFT_REN0608202621879") == "REN0608202621879"
    # No code -> first token with a digit, else the whole stem.
    assert _invoice_no_from_filename("timesheet 2026 final") == "2026"
    assert _invoice_no_from_filename("plain-name") == "plain-name"


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
