"""Rule-based invoice extraction using pdfplumber.

Strategy that generalizes across the sample vendors (AVASOFT, CIGNITI, TCS):
- Header fields (vendor, invoice #, date, total, period) via tolerant regexes over the full text.
- Line items via table extraction (more robust than raw text, which inserts stray spaces inside
  numbers). Columns are mapped by header keywords; numeric cells are de-spaced ("8 3.00" -> 83.00).

Returns a partial ParsedInvoice plus a confidence score and warnings so the orchestrator can decide
whether to fall back to the LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pdfplumber
from dateutil import parser as dateparser

from app.schemas import ParsedInvoice, ParsedLineItem


@dataclass
class RulesResult:
    parsed: ParsedInvoice
    confidence: float
    warnings: list[str] = field(default_factory=list)
    text: str = ""
    has_text: bool = True


# --- number / date helpers -------------------------------------------------
def clean_number(s: str | None) -> float | None:
    """'$2,400' -> 2400.0 ; '8 3.00' -> 83.0 ; '180 Hrs' -> 180.0 ; '1 5,936.00' -> 15936.0."""
    if s is None:
        return None
    # keep only digits, dot, comma, spaces; drop currency/units/letters
    t = re.sub(r"[^0-9.,\s]", "", str(s)).strip()
    if not t:
        return None
    t = t.replace(" ", "").replace(",", "")  # de-space mangled numbers, drop thousands sep
    if t.count(".") > 1:  # e.g. stray dots — keep first
        head, _, tail = t.partition(".")
        t = head + "." + tail.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def parse_date(s: str | None) -> date | None:
    """Parse a date, handling both American (MM/DD/YYYY) and European (DD/MM/YYYY) styles.

    Heuristic for numeric dates: if the first component is >12 it must be the day (European);
    if the second is >12 the first is the month (American). When genuinely ambiguous
    (both <=12, e.g. 05/06/2026) we default to American. Truly European-only vendors can be
    forced day-first later via a per-vendor flag.
    """
    if not s:
        return None
    s = s.strip()
    dayfirst = False
    m = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", s)
    if m:
        first, second = int(m.group(1)), int(m.group(2))
        if first > 12 and second <= 12:
            dayfirst = True
        elif second > 12 and first <= 12:
            dayfirst = False
    try:
        return dateparser.parse(s, dayfirst=dayfirst).date()
    except (ValueError, OverflowError):
        return None


# --- header extraction -----------------------------------------------------
# Invoice numbers must contain at least one digit (avoids matching words like "AVASOFT").
_INVOICE_NO_PATTERNS = [
    r"Invoice\s*(?:No|Number|#)\.?\s*:?\s*((?=[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{4,})",
    r"InvoiceNo\.?\s*:?\s*((?=[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{4,})",
    r"\b([A-Z]{2,5}\d{8,})\b",  # fallback: e.g. AVASOFT's "REN0609202621882"
]
_DATE_PATTERNS = [
    r"Invoice\s*Date\s*:?\s*(\d{1,2}[/-][A-Za-z0-9]{2,3}[/-]\d{2,4})",
    r"InvoiceDate\s*:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    r"\bDate\b\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
    r"\b(\d{1,2}/\d{1,2}/\d{4})\b",          # generic fallback (first date in doc)
    r"\b(\d{1,2}-[A-Za-z]{3}-\d{4})\b",
]
# Leading digit required so the capture can't be just whitespace.
_TOTAL_PATTERNS = [
    r"Total\s*Invoice\s*Value\s*:?\s*\$?\s*([0-9][0-9, ]*\.?\d*)",
    r"Total\s*Amount\s*:?\s*\$?\s*([0-9][0-9, ]*\.?\d*)",
    r"Amount\s*Due[^\$\d]*\$?\s*([0-9][0-9, ]*\.?\d*)",
    r"\bTotal\b\s*\(USD\)\s*([0-9][0-9, ]*\.?\d*)",
    r"\bTotal\b\s*\$?\s*([0-9][0-9, ]*\.\d{2})",
    r"\bTotal\b\s*\$\s*([0-9][0-9, ]*)",
]
_VENDOR_PATTERNS = [
    r"Beneficiary\s*Name\s*:?\s*([A-Za-z0-9 .,&]+?)(?:\n|$)",
    r"BeneficiaryName\s*:?\s*([A-Za-z0-9 .,&]+?)(?:\n|$)",
    r"Name\s*of\s*account\s*:?\s*([A-Za-z0-9 .,&]+?)(?:\n|$)",
]
# Period like "04/26/2026 - 05/30/2026" or "01-MAY-26 ... 31-MAY-26" or "01March2026to04April2026"
_PERIOD_PATTERNS = [
    r"(\d{1,2}/\d{1,2}/\d{2,4})\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    r"(\d{1,2}-[A-Za-z]{3}-\d{2,4})\s*(?:to|[-–])\s*(\d{1,2}-[A-Za-z]{3}-\d{2,4})",
    r"(\d{1,2}[A-Za-z]{3,9}\d{4})\s*to\s*(\d{1,2}[A-Za-z]{3,9}\d{4})",
]


def _first_match(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_header(text: str) -> dict:
    vendor = _first_match(_VENDOR_PATTERNS, text)
    if not vendor:
        # Fall back to the first non-empty line (works for AVASOFT / CIGNITI letterheads).
        for line in text.splitlines():
            if line.strip():
                vendor = line.strip()
                break
    period = None
    for p in _PERIOD_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            period = f"{m.group(1)} - {m.group(2)}"
            break
    return {
        "vendor_name": vendor,
        "invoice_number": _first_match(_INVOICE_NO_PATTERNS, text),
        "date_received": parse_date(_first_match(_DATE_PATTERNS, text)),
        "payment_period": period,
        "total_invoice_cost": clean_number(_first_match(_TOTAL_PATTERNS, text)),
    }


# --- line-item extraction (table-based) ------------------------------------
_NAME_KEYS = ("name", "item", "resource", "employee")
_HOURS_KEYS = ("hours", "units", "quantity", "qty")
_RATE_KEYS = ("rate", "price")
_AMOUNT_KEYS = ("amount", "total")
_PERIOD_KEYS = ("period", "from", "to")


def _match_col(header_cells: list[str], keys: tuple[str, ...]) -> int | None:
    for i, c in enumerate(header_cells):
        cl = (c or "").lower()
        if any(k in cl for k in keys):
            return i
    return None


_DATE_TOKEN = r"\d{1,2}[/-][A-Za-z0-9]{2,3}[/-]\d{2,4}|\d{1,2}/\d{1,2}/\d{2,4}"


def _line_period(raw_name: str, from_cell: str | None, to_cell: str | None) -> tuple[date | None, date | None]:
    """Resolve a line's service period from explicit From/To columns or a date range embedded
    in the name cell (e.g. AVASOFT's 'Noorul Sarfaraz 04/26/2026 - 05/30/2026')."""
    if from_cell or to_cell:
        return parse_date(from_cell), parse_date(to_cell)
    dates = re.findall(_DATE_TOKEN, raw_name or "")
    if len(dates) >= 2:
        return parse_date(dates[0]), parse_date(dates[1])
    if len(dates) == 1:
        return parse_date(dates[0]), None
    return None, None


def _name_from_cell(cell: str) -> str:
    """Strip leading titles and any embedded date-range from a name cell."""
    cell = re.sub(r"\b(Mr|Ms|Mrs|Dr)\.?\s*", "", cell, flags=re.IGNORECASE)
    cell = re.split(r"\d{1,2}[/-]", cell)[0]  # drop trailing embedded dates
    return cell.strip()


def extract_line_items_from_tables(tables: list[list[list[str]]]) -> tuple[list[ParsedLineItem], list[str]]:
    warnings: list[str] = []
    items: list[ParsedLineItem] = []

    for table in tables:
        # Find the header row (one that has a name-ish column AND an amount/hours column).
        header_idx = None
        for i, row in enumerate(table[:5]):
            cells = [(c or "") for c in row]
            if _match_col(cells, _NAME_KEYS) is not None and (
                _match_col(cells, _AMOUNT_KEYS) is not None or _match_col(cells, _HOURS_KEYS) is not None
            ):
                header_idx = i
                break
        if header_idx is None:
            continue

        header = [(c or "") for c in table[header_idx]]
        ci_name = _match_col(header, _NAME_KEYS)
        ci_hours = _match_col(header, _HOURS_KEYS)
        ci_rate = _match_col(header, _RATE_KEYS)
        ci_amount = _match_col(header, _AMOUNT_KEYS)
        ci_from = _match_col(header, ("from",))
        ci_to = _match_col(header, ("to",))

        def _cell(cells, ci):
            return cells[ci] if ci is not None and ci < len(cells) else None

        for row in table[header_idx + 1 :]:
            cells = [(c or "").strip() for c in row]
            if not any(cells):
                continue
            raw_name = cells[ci_name] if ci_name is not None and ci_name < len(cells) else ""
            name = _name_from_cell(raw_name)
            # Skip total/footer rows.
            if not name or re.fullmatch(r"(total.*|grand total.*)", name, re.IGNORECASE):
                continue
            if not re.search(r"[A-Za-z]", name):  # name must contain letters
                continue
            hours = clean_number(_cell(cells, ci_hours))
            rate = clean_number(_cell(cells, ci_rate))
            amount = clean_number(_cell(cells, ci_amount))
            # Drop footer/garbage rows that carry a name-ish cell but no numbers.
            if hours is None and rate is None and amount is None:
                continue

            ps, pe = _line_period(raw_name, _cell(cells, ci_from), _cell(cells, ci_to))
            extra: dict = {}
            if ps:
                extra["period_start"] = ps.isoformat()
            if pe:
                extra["period_end"] = pe.isoformat()

            items.append(
                ParsedLineItem(contractor_name=name, hours=hours, rate=rate, amount=amount, extra=extra)
            )
    if not items:
        warnings.append("No line items found via table extraction.")
    return items, warnings


# --- entrypoint ------------------------------------------------------------
def parse_with_rules(pdf_path: str) -> RulesResult:
    warnings: list[str] = []
    text_parts: list[str] = []
    tables: list[list[list[str]]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
            try:
                tables.extend(page.extract_tables() or [])
            except Exception as e:  # pragma: no cover - pdfplumber edge cases
                warnings.append(f"Table extraction error: {e}")

    text = "\n".join(text_parts).strip()
    has_text = bool(text)
    if not has_text:
        warnings.append("PDF has no extractable text (likely scanned) — needs OCR/vision.")
        return RulesResult(ParsedInvoice(), confidence=0.0, warnings=warnings, text="", has_text=False)

    header = extract_header(text)
    items, item_warnings = extract_line_items_from_tables(tables)
    warnings += item_warnings

    parsed = ParsedInvoice(
        vendor_name=header["vendor_name"],
        invoice_number=header["invoice_number"],
        date_received=header["date_received"],
        payment_period=header["payment_period"],
        total_invoice_cost=header["total_invoice_cost"],
        line_items=items,
    )
    # First contractor + their rate/hours surface to the top-level single-contractor fields.
    if items:
        parsed.contractor_name = items[0].contractor_name
        parsed.hourly_or_fixed_rate = items[0].rate
        parsed.hours_worked = items[0].hours

    parsed = parsed  # noqa
    confidence = _score(parsed, warnings)
    return RulesResult(parsed, confidence=confidence, warnings=warnings, text=text, has_text=True)


def _score(p: ParsedInvoice, warnings: list[str]) -> float:
    """Fraction of key signals present, with a bonus when line-item amounts reconcile to the total."""
    checks = [
        bool(p.vendor_name),
        bool(p.invoice_number),
        bool(p.date_received),
        bool(p.total_invoice_cost),
        len(p.line_items) > 0,
    ]
    score = sum(checks) / len(checks)
    if p.line_items and p.total_invoice_cost:
        line_sum = sum((li.amount or 0) for li in p.line_items)
        if line_sum and abs(line_sum - p.total_invoice_cost) <= max(1.0, 0.01 * p.total_invoice_cost):
            score = min(1.0, score + 0.15)
        else:
            warnings.append(
                f"Line-item amounts ({line_sum:,.2f}) do not reconcile to total ({p.total_invoice_cost:,.2f})."
            )
    return round(score, 3)
