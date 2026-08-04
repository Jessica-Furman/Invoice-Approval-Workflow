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
from collections import Counter
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
    tables: list = field(default_factory=list)  # raw pdfplumber tables (for learned templates)


# --- number / date helpers -------------------------------------------------
def clean_number(s: str | None) -> float | None:
    """Parse a money/number string, handling US and European formats.

    '$2,400' -> 2400.0 ; '8 3.00' -> 83.0 ; '180 Hrs' -> 180.0 ; '1 5,936.00' -> 15936.0 ;
    '90 400,00' -> 90400.0 (EU: space=thousands, comma=decimal) ; '1.234,56' -> 1234.56 (EU).
    """
    if s is None:
        return None
    # keep only digits, dot, comma, spaces; drop currency/units/letters
    t = re.sub(r"[^0-9.,\s]", "", str(s)).strip()
    if not t:
        return None
    t = t.replace(" ", "")  # spaces are thousands separators (mangled US or EU) -> drop
    has_comma, has_dot = "," in t, "." in t
    if has_comma and has_dot:
        # The last-occurring separator is the decimal point: US '1,234.56' vs EU '1.234,56'.
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")  # EU: dot=thousands, comma=decimal
        else:
            t = t.replace(",", "")                    # US: comma=thousands, dot=decimal
    elif has_comma:
        # Only a comma: treat as a decimal when it has 1-2 trailing digits ('90400,00'), else thousands.
        t = t.replace(",", ".") if re.search(r",\d{1,2}$", t) else t.replace(",", "")
    if t.count(".") > 1:  # stray/extra dots — keep the first as the decimal point
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
_MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)

# Invoice numbers must contain at least one digit (avoids matching words like "AVASOFT").
_INVOICE_NO_PATTERNS = [
    r"Invoice\s*(?:No|Number|#)\.?\s*:?\s*((?=[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{4,})",
    r"InvoiceNo\.?\s*:?\s*((?=[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{4,})",
    r"\b(INV[-\s]?\d{3,})\b",    # e.g. "INV-0137"
    r"\b([A-Z]{2,5}\d{8,})\b",   # fallback: e.g. AVASOFT's "REN0609202621882"
    r"\bInvoice\s+#?\s*(\d{3,})\b",  # last resort: "INVOICE 1075" (Global Compass) — bare number
]
_DATE_PATTERNS = [
    r"Invoice\s*Date\s*:?\s*(\d{1,2}[/-][A-Za-z0-9]{2,3}[/-]\d{2,4})",
    r"InvoiceDate\s*:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    r"\bDate\b\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
    r"\b(\d{1,2}/\d{1,2}/\d{4})\b",          # generic fallback (first date in doc)
    r"\b(\d{1,2}-[A-Za-z]{3}-\d{4})\b",
    # Month-name date e.g. "Jun 1, 2026" / "JUNE 12, 2026". Anchored on a real month name so a zip code
    # like "Utah 84045" can't be mistaken for a date.
    rf"\b((?:{_MONTH_NAMES})\.?\s+\d{{1,2}},?\s+\d{{4}})\b",
]
# Company-name lines usually carry a legal suffix; used as a vendor fallback.
_COMPANY_SUFFIX_RE = re.compile(
    r"^.*\b(LLC|L\.L\.C\.|Inc\.?|Ltd\.?|Limited|LLP|Corp\.?|Corporation|Technologies|Solutions|Consulting)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
# Leading digit required so the capture can't be just whitespace.
_TOTAL_PATTERNS = [
    r"Total\s*Invoice\s*Value\s*:?\s*\$?\s*([0-9][0-9, ]*\.?\d*)",
    # Ironin: "Total to be paid: 90 400,00 USD (...)" — capture the leading (USD) amount, EU-formatted.
    r"Total\s*to\s*be\s*paid\s*:?\s*\$?\s*([0-9][0-9 .,]*)",
    r"Gross\s*Value\s*:?\s*\$?\s*([0-9][0-9 .,]*\d)",
    r"Total\s*(?:Amount|Due)\s*(?:Due)?\s*:?\s*\$?\s*([0-9][0-9, ]*\.?\d*)",
    r"Amount\s*Due[^\$\d]*\$?\s*([0-9][0-9, ]*\.?\d*)",
    # NextStep & similar: the bold grand total prints as "BALANCE DUE $7,030.00".
    r"Balance\s*Due\s*:?\s*\$?\s*([0-9][0-9, ]*\.?\d*)",
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
    # Month-name ranges like "May 25- June 7, 2026" (Global Compass). Year on the end applies to both.
    r"([A-Z][a-z]{2,8}\.?\s+\d{1,2})\s*[-–]\s*([A-Z][a-z]{2,8}\.?\s+\d{1,2},?\s*\d{4})",
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
        # Prefer a line carrying a company legal suffix (LLC/Inc/Ltd/Technologies/…), skipping the
        # customer (Rent-A-Center / Acima). This is the vendor on most letterheads.
        for m in _COMPANY_SUFFIX_RE.finditer(text):
            cand = m.group(0).strip()
            if cand and not re.search(r"rent-?a-?center|acima", cand, re.IGNORECASE):
                vendor = cand
                break
    if not vendor:
        # Fall back to the first meaningful line, skipping generic document titles.
        _generic = {"invoice", "tax invoice", "bill", "statement", "credit note", "bill to",
                    "invoice date", "date"}
        for line in text.splitlines():
            s = line.strip()
            if s and s.lower() not in _generic:
                vendor = s
                break
    # Period detection, highest priority first:
    #   1. an explicit "Period:" label + range, then 2. a "Time Card" export's actual worked-date
    #   span, then 3. any explicit date range (incl. a long "05 April 2026 to 25 April 2026" form).
    #   These are precise actual-work dates and win.
    #   4. "for the month of <Month> <Year>" and 5. "<Month> <Year> Services" are month-level
    #   fallbacks (whole calendar month), used only when no explicit range is found.
    period = _labeled_period(text)
    if not period:
        period = _billed_from_to_period(text)  # Sogeti "Billed From/To Date" labeled range
    labeled = period is not None
    if not period:
        period = _timecard_actual_period(text)  # "Time Card" export: actual worked dates, not the report's request window
        if period:
            labeled = True
    if not period:
        period = _long_date_range(text)  # "05 April 2026 to 25 April 2026" (tolerates no spaces / line breaks)
    if not period:
        period = _shared_year_range(text)  # "01-Apr to 30-Apr 2026" (year stated once)
    if not period:
        for p in _PERIOD_PATTERNS:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                period = f"{m.group(1)} - {m.group(2)}"
                break
    if not period:
        # "Invoice for the month of April 2026" -> the full calendar month (authoritative billing month).
        month_of = _month_of_period(text)
        if month_of:
            period, labeled = month_of, True
    if not period:
        period = _month_period(text)  # "May 2026 Services" descriptor
    if not period:
        # A bare "Month YYYY" sitting in the document header/title (above the line items), e.g.
        # "Acima Mobile App Timesheet - April 2026" -> that full calendar month.
        period = _header_month_period(text)
    return {
        "vendor_name": _clean_vendor(vendor),
        "invoice_number": _first_match(_INVOICE_NO_PATTERNS, text),
        "date_received": parse_date(_first_match(_DATE_PATTERNS, text)),
        "payment_period": period,
        "payment_period_labeled": labeled,
        "total_invoice_cost": clean_number(_first_match(_TOTAL_PATTERNS, text)),
    }


_PERIOD_LABEL_RE = re.compile(r"(pay\s*period|service\s*period|billing\s*period|period)", re.IGNORECASE)

# Sogeti/Capgemini: a "Billed From Date ... Billed To Date" label, then the two dates — which a
# two-column layout can push onto a later line behind other text — so allow a gap before the pair.
_BILLED_FROM_TO_RE = re.compile(
    r"Billed\s*From\s*Date.{0,200}?"
    r"(\d{1,2}-[A-Za-z]{3}-\d{2,4})\s+(\d{1,2}-[A-Za-z]{3}-\d{2,4})",
    re.IGNORECASE | re.DOTALL,
)


def _billed_from_to_period(text: str) -> str | None:
    """A labeled 'Billed From Date / Billed To Date' range -> 'start - end' (authoritative)."""
    m = _BILLED_FROM_TO_RE.search(text)
    return f"{m.group(1)} - {m.group(2)}" if m else None


# A "Time Card by company invoice" export (Odyssey and similar timekeeping systems) always prints
# its REQUESTED reporting window as a header (e.g. "06/01/2026 - 06/30/2026"), even when the
# contractor's actual work stopped partway through — a mid-period end date wouldn't shrink that
# header. The true worked span is the min/max of the populated "Date" column in the daily table
# below it (e.g. rows through "06/19/2026 Fri Work 8.00 8.00 8.00"), so derive the period from
# those rows instead of trusting the header range.
_TIMECARD_TITLE_RE = re.compile(r"Time\s*Card\s*by\s*company\s*invoice", re.IGNORECASE)
_TIMECARD_DATE_ROW_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4})\s+[A-Za-z]{3}\s+\S", re.MULTILINE)


def _timecard_actual_period(text: str) -> str | None:
    """Actual worked-date span from a 'Time Card by company invoice' daily table (see note above)."""
    if not _TIMECARD_TITLE_RE.search(text):
        return None
    dates = sorted({d for s in _TIMECARD_DATE_ROW_RE.findall(text) if (d := parse_date(s))})
    if not dates:
        return None
    start, end = dates[0], dates[-1]
    return f"{start.month}/{start.day}/{start.year} - {end.month}/{end.day}/{end.year}"

# A trailing date/month descriptor tacked onto a vendor/title line, e.g. "… - April 2026" or
# "Odyssey Information Services, Inc. 4/30/2026" — noise that shouldn't be part of the vendor name.
_VENDOR_TRAILING_DATE_RE = re.compile(
    rf"\s*[-–]?\s*(?:"
    rf"(?:{_MONTH_NAMES})\.?\s+\d{{4}}"                 # April 2026
    rf"|\d{{1,2}}[-/][A-Za-z]{{3}}[-/]\d{{2,4}}"        # 31-MAY-2026
    rf"|\d{{1,2}}/\d{{1,2}}/\d{{2,4}}"                  # 4/30/2026
    rf")\s*$",
    re.IGNORECASE,
)


def _clean_vendor(name: str | None) -> str | None:
    """Strip a trailing date/month-year descriptor (and a leftover separator) off a vendor name."""
    if not name:
        return name
    prev = None
    while prev != name:
        prev = name
        name = _VENDOR_TRAILING_DATE_RE.sub("", name).strip().rstrip("-–").strip()
    return name or None
# "May 2026 Services" / "April 2026 Service" — a month descriptor for the work billed.
_MONTH_PERIOD_RE = re.compile(rf"\b({_MONTH_NAMES})\s+(\d{{4}})\s+Servic", re.IGNORECASE)
# "Invoice for the month of April 2026" — tolerant of missing spaces (pdfplumber concatenates words).
_MONTH_OF_RE = re.compile(
    rf"for\s*the\s*month\s*of\s*({_MONTH_NAMES})\.?,?\s*(\d{{4}})", re.IGNORECASE
)


def _full_month_period(month_name: str, year: str) -> str | None:
    """'April', '2026' -> 'M/1/YYYY - M/last/YYYY' covering the whole calendar month."""
    import calendar

    start = parse_date(f"{month_name} 1, {year}")
    if start is None:
        return None
    last_day = calendar.monthrange(start.year, start.month)[1]
    return f"{start.month}/{start.day}/{start.year} - {start.month}/{last_day}/{start.year}"


def _month_period(text: str) -> str | None:
    """Derive a full-calendar-month period string from a 'Month YYYY Service(s)' descriptor."""
    m = _MONTH_PERIOD_RE.search(text)
    return _full_month_period(m.group(1), m.group(2)) if m else None


def _month_of_period(text: str) -> str | None:
    """Derive a full-calendar-month period from an 'Invoice for the month of <Month> <Year>' phrase."""
    m = _MONTH_OF_RE.search(text)
    return _full_month_period(m.group(1), m.group(2)) if m else None


# A bare "Month YYYY" (e.g. "April 2026"). 4-digit year required, so per-line day-dates like
# "1-Apr-26" can't match. Searched only in the header so a stray month elsewhere isn't mistaken.
_BARE_MONTH_RE = re.compile(rf"\b({_MONTH_NAMES})\.?\s+(\d{{4}})\b", re.IGNORECASE)


def _header_month_period(text: str) -> str | None:
    """A bare 'Month YYYY' in the document header/title (the lines above the line items) implies
    that full calendar month, even with no 'Period:'/'for the month of' label (e.g. a timesheet
    titled 'Acima Mobile App Timesheet - April 2026')."""
    head = "\n".join(text.splitlines()[:6])
    m = _BARE_MONTH_RE.search(head)
    return _full_month_period(m.group(1), m.group(2)) if m else None


# "05 April 2026 to 25 April 2026" — month-name range with a year on each end. Tolerant of missing
# spaces and line breaks (pdfplumber concatenates and wraps), since both halves are rebuilt cleanly.
_LONG_DATE_RANGE_RE = re.compile(
    rf"(\d{{1,2}})\s*({_MONTH_NAMES})\.?\s*,?\s*(\d{{4}})"
    rf"\s*(?:to|through|–|-)\s*"
    rf"(\d{{1,2}})\s*({_MONTH_NAMES})\.?\s*,?\s*(\d{{4}})",
    re.IGNORECASE,
)


def _long_date_range(text: str) -> str | None:
    """Parse a 'DD Month YYYY to DD Month YYYY' range into a clean 'M/D/Y - M/D/Y' string."""
    m = _LONG_DATE_RANGE_RE.search(text)
    if not m:
        return None
    d1, mon1, y1, d2, mon2, y2 = m.groups()
    start, end = parse_date(f"{mon1} {d1}, {y1}"), parse_date(f"{mon2} {d2}, {y2}")
    if start and end:
        return f"{start.month}/{start.day}/{start.year} - {end.month}/{end.day}/{end.year}"
    return None


# "01-Apr to 30-Apr 2026" — month-name day range with the year given only once (applies to both ends).
_SHARED_YEAR_RANGE_RE = re.compile(
    rf"(\d{{1,2}})\s*[-/ ]\s*({_MONTH_NAMES})\.?"
    rf"\s*(?:to|through|–|-)\s*"
    rf"(\d{{1,2}})\s*[-/ ]\s*({_MONTH_NAMES})\.?\s*,?\s*(\d{{4}})",
    re.IGNORECASE,
)


def _shared_year_range(text: str) -> str | None:
    """Parse 'DD-Mon to DD-Mon YYYY' (year stated once) into a clean 'M/D/Y - M/D/Y' string."""
    m = _SHARED_YEAR_RANGE_RE.search(text)
    if not m:
        return None
    d1, mon1, d2, mon2, yr = m.groups()
    start, end = parse_date(f"{mon1} {d1}, {yr}"), parse_date(f"{mon2} {d2}, {yr}")
    if start and end:
        return f"{start.month}/{start.day}/{start.year} - {end.month}/{end.day}/{end.year}"
    return None


# "June 1-14, 2026" — a day range within a single month; the year applies to both ends.
_SAME_MONTH_RANGE_RE = re.compile(
    rf"\b({_MONTH_NAMES})\.?\s+(\d{{1,2}})\s*[-–]\s*(\d{{1,2}}),?\s*(\d{{4}})", re.IGNORECASE
)


def _same_month_day_range(text: str) -> str | None:
    """Expand a same-month day range like 'June 1-14, 2026' into 'June 1, 2026 - June 14, 2026'."""
    m = _SAME_MONTH_RANGE_RE.search(text)
    if not m:
        return None
    mon, d1, d2, yr = m.group(1), m.group(2), m.group(3), m.group(4)
    return f"{mon} {d1}, {yr} - {mon} {d2}, {yr}"


def _labeled_period(text: str) -> str | None:
    """A date range on the same line as a 'Period' label (e.g. 'Period: 5/10/2026 - 5/29/2026')."""
    for line in text.splitlines():
        if _PERIOD_LABEL_RE.search(line):
            for p in _PERIOD_PATTERNS:
                m = re.search(p, line, re.IGNORECASE)
                if m:
                    return f"{m.group(1)} - {m.group(2)}"
            same_month = _same_month_day_range(line)  # "Period: June 1-14, 2026"
            if same_month:
                return same_month
    return None


# --- line-item extraction (table-based) ------------------------------------
_NAME_KEYS = ("name", "item", "resource", "employee", "description", "consultant", "contractor", "activity")
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


# --- person-name extraction (pull a human name out of a description line) --
# Words that are never part of a contractor's name — they break a candidate name run. Covers
# service descriptions, units/columns, company suffixes, connectors, and month names (dates).
_NON_NAME_WORDS = {
    "it", "consultancy", "consulting", "consultant", "development", "developement", "services",
    "service", "software", "engineering", "engineer", "professional", "contractor", "contractors",
    "invoice", "invoicing", "support", "maintenance", "quality", "assurance", "design", "testing",
    "team", "solutions", "solution", "technologies", "technology", "systems", "labs", "studio",
    "inc", "llc", "ltd", "limited", "corp", "corporation", "llp", "gmbh", "sp", "zoo", "company",
    "provided", "performed", "rendered", "monthly", "weekly", "hourly", "hours", "hour", "rate",
    "amount", "total", "subtotal", "balance", "due", "tax", "activity", "quantity", "qty",
    "description", "period", "and", "the", "of", "for", "by", "to", "from",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    # Roles / titles that trail a name (e.g. "Bibin Roy - Lead", "… - Developer").
    "lead", "developer", "developers", "tester", "analyst", "architect", "designer", "manager",
    "intern", "associate", "senior", "junior", "principal", "staff", "scrum", "devops",
    "specialist", "coordinator", "administrator", "admin", "trainee", "freelancer",
    # Project / product descriptor words that precede a name on some invoices.
    "mobile", "app", "application", "web", "project", "module", "phase", "portal", "platform",
}
# Lowercase nobiliary particles that may sit *inside* a name (e.g. "Maria de Souza", "van der Berg").
# They may continue a run but can't start or end it.
_NAME_PARTICLES = {
    "de", "del", "della", "da", "das", "dos", "di", "du", "van", "von", "der", "den", "ten",
    "ter", "la", "le", "el", "bin", "binti", "al", "y", "e",
}
# Explicit connector → the name usually follows it (rule 6: pick the actual contractor).
_NAME_CONNECTOR_RE = re.compile(
    r"\b(?:provided\s+by|performed\s+by|rendered\s+by|services?\s+for|invoice\s+for|"
    r"contractor|consultant|resource|employee|name|for|by)\b\s*[:\-–]?\s*(.+)$",
    re.IGNORECASE,
)


def _name_token_ok(tok: str) -> bool:
    """A single name word: capitalized (unicode-aware), not an acronym, not a description word."""
    core = tok.strip(".")
    if not core or not core[0].isalpha() or not core[0].isupper():
        return False
    if core.lower() in _NON_NAME_WORDS:
        return False
    if len(core) == 1:
        return True  # initial, e.g. the "R" in "Sachin R Gangolli"
    if core.isupper():
        return False  # ALL-CAPS acronym / company token (IT, USD, BILL)
    return True


def _best_name_in(text: str) -> str | None:
    """Return the most likely 2–4 word human name in a fragment, or None.

    Splits into tokens and finds maximal runs of capitalized name words (nobiliary particles like
    'de'/'van' may sit inside a run). Returns the first run of 2–4 words in document order.
    """
    tokens = [t for t in re.split(r"[^\w'’.\-]+", text or "", flags=re.UNICODE) if t]
    runs: list[list[str]] = []
    run: list[str] = []
    for tok in tokens:
        if _name_token_ok(tok):
            run.append(tok)
        elif run and tok.lower() in _NAME_PARTICLES:
            run.append(tok.lower())  # continue through a particle
        else:
            if run:
                runs.append(run)
            run = []
    if run:
        runs.append(run)

    for r in runs:
        while r and r[0].lower() in _NAME_PARTICLES:  # can't start with a particle
            r = r[1:]
        while r and r[-1].lower() in _NAME_PARTICLES:  # nor end with one
            r = r[:-1]
        if 2 <= len(r) <= 4:
            return " ".join(r)
    return None


# Any date form that can appear inside a name cell, used to locate the name relative to the dates.
_ANY_DATE_RE = re.compile(
    r"\d{1,2}/\d{1,2}/\d{2,4}"                                  # 04/26/2026
    r"|\d{1,2}\s*[-/]\s*[A-Za-z]{3,9}(?:\s*[-/]\s*\d{2,4})?"    # 01-Apr / 01-Apr-2026 / 01 Apr
    rf"|\b(?:{_MONTH_NAMES})\.?\s*\d{{4}}"                      # April 2026
    r"|\b\d{4}\b",                                              # 2026
    re.IGNORECASE,
)


def extract_person_name(raw: str | None) -> str | None:
    """Extract a human contractor name from a cell that may be a longer description line.

    The name can sit anywhere — alone, inside a description, or (common on AVASOFT/Coforge) after a
    project label and a date range, e.g. "Mobile App Development - 01-Apr to 30-Apr 2026 - Bibin Roy
    - Lead". Priority: (1) a name in parentheses, (2) text after a connector ("provided by" /
    "Contractor:"), (3) date-anchored — the segment after the last date, then before the first date,
    (4) the best capitalized run anywhere. Returns None if no clear person name is present.
    """
    if not raw:
        return None
    s = raw.replace("\n", " ").strip()
    for inner in re.findall(r"\(([^)]*)\)", s):  # (1) parentheses win
        nm = _best_name_in(inner)
        if nm:
            return nm
    m = _NAME_CONNECTOR_RE.search(s)  # (2) after a connector
    if m:
        nm = _best_name_in(m.group(1))
        if nm:
            return nm
    # (3) Date-anchored: the contractor is usually next to the worked dates — after them on these
    # invoices, before them on others. Try the tail after the last date, then the head before the first.
    dates = list(_ANY_DATE_RE.finditer(s))
    if dates:
        for fragment in (s[dates[-1].end():], s[: dates[0].start()]):
            nm = _best_name_in(fragment)
            if nm:
                return nm
    return _best_name_in(s)  # (4) anywhere


def _name_from_cell(cell: str) -> str:
    """Pull the contractor's human name out of a cell that may wrap it in a description.

    Falls back to the old title/date stripping when no clear person name is detected, so plain
    name cells (and unusual single-token names) are preserved unchanged.
    """
    person = extract_person_name(cell)
    if person:
        return person
    cell = re.sub(r"\b(Mr|Ms|Mrs|Dr)\.?\s*", "", cell, flags=re.IGNORECASE)
    cell = re.split(r"\d{1,2}[/-]", cell)[0]  # drop trailing embedded dates
    return cell.strip()


def _cell(cells: list[str], ci: int | None) -> str | None:
    return cells[ci] if ci is not None and ci < len(cells) else None


def _parse_one_table(table: list[list[str]]) -> list[ParsedLineItem]:
    # Find the header row. Require a name column AND an hours/units column: per-contractor tables
    # always have hours, while generic "Description / Amount" summary tables don't — so this skips
    # summary tables that would otherwise look like line items.
    header_idx = None
    for i, row in enumerate(table[:5]):
        cells = [(c or "") for c in row]
        if _match_col(cells, _NAME_KEYS) is not None and _match_col(cells, _HOURS_KEYS) is not None:
            header_idx = i
            break
    if header_idx is None:
        return []

    header = [(c or "") for c in table[header_idx]]
    ci_name = _match_col(header, _NAME_KEYS)
    ci_hours = _match_col(header, _HOURS_KEYS)
    ci_rate = _match_col(header, _RATE_KEYS)
    ci_amount = _match_col(header, _AMOUNT_KEYS)
    ci_from = _match_col(header, ("from",))
    ci_to = _match_col(header, ("to",))

    numeric_cols = [c for c in (ci_hours, ci_rate, ci_amount) if c is not None]
    first_numeric = min(numeric_cols) if numeric_cols else None

    items: list[ParsedLineItem] = []
    for row in table[header_idx + 1 :]:
        cells = [(c or "").strip() for c in row]
        if not any(cells):
            continue
        raw_name = cells[ci_name] if ci_name is not None and ci_name < len(cells) else ""
        name = _name_from_cell(raw_name)
        # Merged cells can shift the name one column over from its header; if the mapped cell has
        # no letters, take the first alphabetic cell to the left of the numeric columns.
        if not re.search(r"[A-Za-z]", name):
            limit = first_numeric if first_numeric is not None else len(cells)
            for j in range(0, min(limit, len(cells))):
                cand = cells[j]
                if cand and re.search(r"[A-Za-z]", cand):
                    name = _name_from_cell(cand)
                    break
        # Skip total/footer rows (e.g. "Total", "Grand Total", "Balance Due", "Subtotal", "Amount Due").
        if not name or re.match(
            r"(grand\s+total|sub\s*total|total|balance(\s+due)?|amount\s+due|tax)\b",
            name,
            re.IGNORECASE,
        ):
            continue
        if not re.search(r"[A-Za-z]", name):  # name must contain letters
            continue
        hours = clean_number(_cell(cells, ci_hours))
        rate = clean_number(_cell(cells, ci_rate))
        amount = clean_number(_cell(cells, ci_amount))
        # Drop footer/garbage rows that carry a name-ish cell but no numbers.
        if hours is None and rate is None and amount is None:
            continue
        # If the amount cell was merged/shifted, derive it from hours x rate.
        if amount is None and hours is not None and rate is not None:
            amount = round(hours * rate, 2)

        ps, pe = _line_period(raw_name, _cell(cells, ci_from), _cell(cells, ci_to))
        extra: dict = {}
        if ps:
            extra["period_start"] = ps.isoformat()
        if pe:
            extra["period_end"] = pe.isoformat()

        items.append(
            ParsedLineItem(contractor_name=name, hours=hours, rate=rate, amount=amount, extra=extra)
        )
    return items


def extract_line_items_from_tables(tables: list[list[list[str]]]) -> tuple[list[ParsedLineItem], list[str]]:
    """Parse each candidate table and return the one yielding the most line items.

    Invoices often contain several tables (e.g. a one-row page-1 summary plus the real per-contractor
    annexure); picking the table with the most valid rows avoids treating a summary line as a contractor.
    """
    warnings: list[str] = []
    best: list[ParsedLineItem] = []
    for table in tables:
        items = _parse_one_table(table)
        if len(items) > len(best):
            best = items
    if not best:
        warnings.append("No line items found via table extraction.")
    return best, warnings


# --- "Services Rendered for:" multi-contractor billing (e.g. Gravity IT Resources) ----------
# This vendor lists each contractor as "Services Rendered for: <Last, First> - <Role>" with matching
# Quantity/Rate/Amount, but pdfplumber crams several contractors into one row as newline-joined cells.
_SERVICES_RENDERED_RE = re.compile(r"Services\s+Rendered\s+for:\s*(.+)", re.IGNORECASE)


def _services_rendered_name(line: str) -> str:
    """'Yaga, Anusha - Product Manager' -> 'Yaga, Anusha' (drop the trailing ' - <role>')."""
    return re.split(r"\s+-\s+", line.strip(), maxsplit=1)[0].strip()


def parse_services_rendered(tables: list[list[list[str]]]) -> list[ParsedLineItem]:
    """Extract every "Services Rendered for: <Name>" billing line across all tables/pages.

    Each column's cell may hold several values joined by newlines (one per contractor). We pull the
    names from the description column and zip them, by index, with the Quantity/Rate/Amount columns.
    """
    items: list[ParsedLineItem] = []
    for table in tables:
        if not table or not table[0]:
            continue
        header = [(c or "") for c in table[0]]
        ci_name = _match_col(header, ("description", "item"))
        ci_hours = _match_col(header, _HOURS_KEYS)
        ci_rate = _match_col(header, _RATE_KEYS)
        ci_amount = _match_col(header, _AMOUNT_KEYS)
        if ci_name is None or ci_hours is None:
            continue
        for row in table[1:]:
            cells = [(c or "") for c in row]
            desc = cells[ci_name] if ci_name < len(cells) else ""
            if "services rendered for" not in desc.lower():
                continue
            names = [
                _services_rendered_name(m.group(1))
                for line in desc.split("\n")
                if (m := _SERVICES_RENDERED_RE.search(line))
            ]

            def _col(ci: int | None) -> list[str]:
                if ci is None or ci >= len(cells):
                    return []
                return [v.strip() for v in cells[ci].split("\n") if v.strip()]

            hrs, rates, amts = _col(ci_hours), _col(ci_rate), _col(ci_amount)
            for i, raw_name in enumerate(names):
                name = _name_from_cell(raw_name) or raw_name
                hours = clean_number(hrs[i]) if i < len(hrs) else None
                rate = clean_number(rates[i]) if i < len(rates) else None
                amount = clean_number(amts[i]) if i < len(amts) else None
                if amount is None and hours is not None and rate is not None:
                    amount = round(hours * rate, 2)
                items.append(
                    ParsedLineItem(contractor_name=name, hours=hours, rate=rate, amount=amount)
                )
    return items


# --- "Name ...Billable N Hours @ rate" text lines (Sogeti / Capgemini) ----------------------
# Each line item is plain text the table extractor can't read, e.g.:
#   "1 Akde, Sridevi ...Billable 189.00 Hours @ 20.00 No 3,780.00 3,780.00"
# The rate may wrap to the next line ("@ No <amount>\n25.00") or the row may be truncated at a page
# break — so "Hours" and "@ rate" are optional; we always capture the name and hours.
_BILLABLE_LINE_RE = re.compile(
    r"^\s*\d+\s+(.+?)\s*\.{2,}\s*Billable\s+([\d,]+\.?\d*)(?:\s*Hours)?(?:\s*@\s*([\d,]+\.?\d*))?",
    re.MULTILINE,
)


def parse_billable_lines(text: str) -> list[ParsedLineItem]:
    """Parse '<#> <Last, First> ...Billable <hours> Hours @ <rate>' text line items."""
    items: list[ParsedLineItem] = []
    for m in _BILLABLE_LINE_RE.finditer(text):
        name = m.group(1).strip().rstrip(".").strip()
        hours = clean_number(m.group(2))
        if not name or hours is None:
            continue
        rate = clean_number(m.group(3)) if m.group(3) else None
        amount = round(hours * rate, 2) if rate is not None else None
        items.append(ParsedLineItem(contractor_name=name, hours=hours, rate=rate, amount=amount))
    return items


# --- "Qty | Item | Rate | Amount" text rows (Odyssey) --------------------------------------
# A simple invoice whose data row sits in the text, not a real table, e.g.:
#   "Qty Item Rate Amount"
#   "176 Shanda Wright $93.00 $16,368.00"   (Qty=hours, Item=contractor name)
_QTY_ITEM_HEADER_RE = re.compile(
    r"\bQ(?:ty|uantity)\b.*\bItem\b|\bItem\b.*\bQ(?:ty|uantity)\b", re.IGNORECASE
)
_QTY_ITEM_ROW_RE = re.compile(
    r"^[ \t]*(\d+(?:[.,]\d+)?)[ \t]+([A-Za-z][^$\d\n]*?)[ \t]+"
    r"\$?[ \t]*([\d,]+(?:\.\d+)?)[ \t]+\$?[ \t]*([\d,]+(?:\.\d+)?)[ \t]*$",
    re.MULTILINE,
)


def parse_qty_item_lines(text: str) -> list[ParsedLineItem]:
    """Parse 'Qty Item Rate Amount' invoices where the row is '<hours> <name> $<rate> $<amount>'.

    Only runs when a 'Qty … Item' header is present, so footer lines (Subtotal/Tax/Total) and stray
    numbers aren't mistaken for line items.
    """
    if not _QTY_ITEM_HEADER_RE.search(text):
        return []
    items: list[ParsedLineItem] = []
    for m in _QTY_ITEM_ROW_RE.finditer(text):
        name = m.group(2).strip()
        hours = clean_number(m.group(1))
        if not name or hours is None:
            continue
        items.append(
            ParsedLineItem(
                contractor_name=name,
                hours=hours,
                rate=clean_number(m.group(3)),
                amount=clean_number(m.group(4)),
            )
        )
    return items


# --- "DESCRIPTION | QTY | RATE | AMOUNT" text invoices (NextStep Recruiting & same shape) ----
# A clean columnar invoice whose rows live in the text layer rather than a ruled table, so pdfplumber
# only reads the header. The header is "DESCRIPTION QTY RATE AMOUNT" and each contractor row is:
#   "Stephen Dickison-Scrum Master-Reg Hours (5/31/26-6/6/26) 34 95.00 3,230.00"
# i.e. under DESCRIPTION the contractor name leads, followed by role/hours-type descriptors and the
# worked period in parentheses; QTY is the hours, RATE the unit rate, AMOUNT the line total. The
# trailing "<hours> <rate.dd> <amount.dd>" triple anchors each row, so footer lines that carry only one
# number ("BALANCE DUE $7,030.00") and bank-detail lines are ignored. The period in parentheses is
# captured per line so the invoice's full span is recovered even though there's no header "Period:".
_DESC_QTY_HEADER_RE = re.compile(r"\bDescription\b.*\bQ(?:ty|uantity)\b.*\bAmount\b", re.IGNORECASE)
_DESC_QTY_ROW_RE = re.compile(
    r"^(?P<desc>.+?)\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<rate>[\d,]+\.\d{2})\s+\$?\s*(?P<amount>[\d,]+\.\d{2})\s*$"
)


def _desc_qty_name(desc: str) -> str:
    """Recover the contractor name from a 'Name-Role-HoursType (period)' description.

    The name leads the description; role/hours-type text follows after a hyphen and the worked period
    sits in parentheses. Take the text before the parenthetical and before the first hyphen, then tidy
    it through the person-name detector (which also trims any role words on a space-separated form)."""
    head = re.split(r"\(", desc, maxsplit=1)[0]          # drop the "(period)" tail
    head = re.split(r"\s*[-–]\s*", head, maxsplit=1)[0]  # text before the first hyphen (role separator)
    return _best_name_in(head) or head.strip()


def parse_desc_qty_rate_amount(text: str) -> list[ParsedLineItem]:
    """Parse 'DESCRIPTION QTY RATE AMOUNT' invoices (NextStep Recruiting & same-shape vendors).

    QTY is the hours worked, RATE the unit rate, AMOUNT the line total. Gated on the
    "DESCRIPTION … QTY … AMOUNT" header so it only runs for this layout, and only on lines ending in a
    "<hours> <rate> <amount>" numeric triple so headers, footers and bank-detail lines are skipped.
    """
    if not _DESC_QTY_HEADER_RE.search(text):
        return []
    items: list[ParsedLineItem] = []
    for raw in text.splitlines():
        m = _DESC_QTY_ROW_RE.match(raw.strip())
        if not m:
            continue
        desc = m.group("desc").strip()
        name = _desc_qty_name(desc)
        if not name or not re.search(r"[A-Za-z]", name):
            continue
        if re.match(r"(grand\s+total|sub\s*total|total|balance(\s+due)?|amount\s+due|tax)\b",
                    name, re.IGNORECASE):
            continue
        ps, pe = _line_period(desc, None, None)
        extra: dict = {}
        if ps:
            extra["period_start"] = ps.isoformat()
        if pe:
            extra["period_end"] = pe.isoformat()
        items.append(
            ParsedLineItem(
                contractor_name=name,
                hours=clean_number(m.group("qty")),
                rate=clean_number(m.group("rate")),
                amount=clean_number(m.group("amount")),
                extra=extra,
            )
        )
    return items


# --- Cognizant "Name Location TimeType Efforts UOM Rate NetBilling" text rows ---------------
# Cognizant invoices aren't ruled tables — each contractor is a single text line:
#   "Pérez de la Cruz,Gerardo Onsite RTIME 144.00 MHR 70.00 10,080.00"
# columns: Name(Last,First) | Location | TimeType | Efforts(hours) | UOM | Rate | Net Billing(amount).
# The accented name often arrives mojibaked (é -> U+FFFD) from the text layer; repaired via OCR later
# by repair_mojibake_names(). The trailing "<hours> <UOM> <rate> <amount>" block anchors the row.
_COGNIZANT_LINE_RE = re.compile(
    r"^(?P<prefix>.+?)\s+(?P<hours>[\d,]+\.\d{2})\s+(?P<uom>[A-Za-z]{2,4})\s+"
    r"(?P<rate>[\d,]+\.\d{2})\s+(?P<amount>[\d,]+\.\d{2})\s*$"
)
# Units we accept in the UOM column (rejects e.g. a trailing currency "USD" on a totals line).
_COGNIZANT_UOM = {"mhr", "hr", "hrs", "hour", "hours", "day", "days"}
# Delivery-location / time-type tokens that trail the name before the numeric columns.
_COGNIZANT_TRAIL = {"onsite", "offshore", "onshore", "offsite", "remote", "rtime", "otime", "ot", "time"}


def parse_cognizant_lines(text: str) -> list[ParsedLineItem]:
    """Parse Cognizant rows '<Name> <Location> <TimeType> <hours> <UOM> <rate> <amount>'.

    Name keeps its raw 'Last, First' form (matching is order-insensitive downstream). Mojibaked
    accents are left as U+FFFD here and fixed by repair_mojibake_names() using OCR.
    """
    items: list[ParsedLineItem] = []
    for raw in text.splitlines():
        m = _COGNIZANT_LINE_RE.match(raw.strip())
        if not m or m.group("uom").lower() not in _COGNIZANT_UOM:
            continue
        toks = m.group("prefix").split()
        while toks and toks[-1].lower().strip(".,") in _COGNIZANT_TRAIL:  # drop location/time-type
            toks.pop()
        name = " ".join(toks).strip()
        if not name or not re.search(r"[A-Za-z�]", name):
            continue
        if re.match(r"(grand\s+total|sub\s*total|total|amount\s+due)\b", name, re.IGNORECASE):
            continue
        items.append(
            ParsedLineItem(
                contractor_name=name,
                hours=clean_number(m.group("hours")),
                rate=clean_number(m.group("rate")),
                amount=clean_number(m.group("amount")),
            )
        )
    return items


def repair_mojibake_names(items: list[ParsedLineItem], ocr_text: str, threshold: float = 80.0) -> None:
    """Replace contractor names the PDF text layer mangled (accented char -> U+FFFD) with the clean
    version OCR reads. Each mojibake name is matched to its best-scoring OCR line by fuzzy ratio.

    Mutates `items` in place. A no-op for names without U+FFFD. OCR reads glyphs like 'é' that the
    embedded text layer can't map (Cognizant), so OCR is the source of truth for the accented form.
    """
    from rapidfuzz import fuzz

    candidates = [l.strip() for l in ocr_text.splitlines() if l.strip() and "�" not in l]
    if not candidates:
        return
    for li in items:
        nm = li.contractor_name
        if not nm or "�" not in nm:
            continue
        target = nm.replace("�", "").lower()
        best, best_score = None, 0.0
        for cand in candidates:
            score = fuzz.ratio(target, cand.lower())
            if score > best_score:
                best, best_score = cand, score
        if best and best_score >= threshold:
            li.contractor_name = best


# --- text-layout fallback (no real table) ----------------------------------
# Matches lines like "Hours- Cristian Vargas- $65/hr" (Global Compass style rate lists).
_RATE_LINE_RE = re.compile(r"Hours\s*-\s*([A-Za-z][A-Za-z .'\-]+?)\s*-\s*\$\s*(\d+(?:\.\d+)?)\s*/\s*hr", re.IGNORECASE)
_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*hours", re.IGNORECASE)
_MONEY_RE = re.compile(r"\$\s*([\d,]+\.\d{2})")


def parse_rate_list_text(text: str) -> list[ParsedLineItem]:
    """Parse 'Hours- Name- $rate/hr ... N hours ... $amount' rate-list invoices from raw text.

    Each contractor contributes exactly one name+rate, one 'N hours', and one '$amount' in document
    order, so we extract each list and zip them. The trailing grand-total $ (e.g. 'TOTAL DUE $...')
    is dropped by only taking as many amounts as there are contractors.
    """
    names_rates = _RATE_LINE_RE.findall(text)
    if not names_rates:
        return []
    hours_list = _HOURS_RE.findall(text)
    amounts = _MONEY_RE.findall(text)

    items: list[ParsedLineItem] = []
    for i, (name, rate) in enumerate(names_rates):
        hours = clean_number(hours_list[i]) if i < len(hours_list) else None
        amount = clean_number(amounts[i]) if i < len(amounts) else None
        items.append(
            ParsedLineItem(
                contractor_name=name.strip(),
                hours=hours,
                rate=clean_number(rate),
                amount=amount,
            )
        )
    return items


# --- Global Compass "PAY PERIOD | BILLABLE | DESCRIPTION | TOTAL" invoices -------------------
# Each contractor row carries its own pay period ("March 1-15, 2026"), a "Hours- <Name>[- ] $<rate>/hr",
# "<N> hours", and a "$<amount>". pdfplumber jumbles the column order per row (and the dash before the
# rate is inconsistent), so the generic rate-list parser mis-zips it. Instead we split the flattened
# text on the pay-period markers and pull each contractor's fields out of the chunk that follows — which
# also captures the per-line period the period-priority logic needs.
# The trailing year is optional: on some GC invoices the period's year is orphaned onto a separate
# line ("May 25- June 7," ... then "2026" lower down), so it isn't adjacent. When absent we fall back
# to the invoice's year (the most common 4-digit year in the document).
_GC_PERIOD_RE = re.compile(
    rf"({_MONTH_NAMES})\s+(\d{{1,2}})\s*[-–]\s*(?:({_MONTH_NAMES})\s+)?(\d{{1,2}}),?(?:\s*(\d{{4}}))?",
    re.IGNORECASE,
)
_GC_NAME_RE = re.compile(r"Hours\s*-\s*(.+?)\s*-?\s*\$\s*\d", re.IGNORECASE)
_GC_RATE_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)\s*/\s*hr", re.IGNORECASE)
_GC_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*hours", re.IGNORECASE)
_GC_AMOUNT_RE = re.compile(r"\$\s*([\d,]+\.\d{2})")
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _gc_period_dates(m: re.Match, default_year: str | None) -> tuple[date | None, date | None]:
    """Resolve a pay-period match to (start, end). Handles same-month ('March 1-15, 2026') and
    cross-month ('May 25 - June 7, 2026') ranges; the year applies to both ends and falls back to the
    document year when not printed next to the period."""
    mon1, d1, mon2, d2, yr = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    yr = yr or default_year
    if not yr:
        return None, None
    return parse_date(f"{mon1} {d1}, {yr}"), parse_date(f"{mon2 or mon1} {d2}, {yr}")


def parse_global_compass(text: str) -> list[ParsedLineItem]:
    """Parse Global Compass rate-list invoices, one line item per contractor with its pay period."""
    flat = re.sub(r"\s+", " ", text)
    periods = list(_GC_PERIOD_RE.finditer(flat))
    if not periods:
        return []
    # Don't let the grand total ("TOTAL DUE $...") be parsed as a contractor.
    cut = flat.lower().find("total due")
    end_cut = cut if cut != -1 else len(flat)
    # Fallback year for periods whose year is orphaned on another line: the doc's most common year.
    years = _YEAR_RE.findall(flat)
    default_year = Counter(years).most_common(1)[0][0] if years else None

    items: list[ParsedLineItem] = []
    for i, m in enumerate(periods):
        rec_end = periods[i + 1].start() if i + 1 < len(periods) else end_cut
        record = flat[m.end():rec_end]
        nm = _GC_NAME_RE.search(record)
        if not nm:
            continue
        name = nm.group(1).strip().rstrip("-").strip()
        if not name:
            continue
        rate_m, hours_m, amount_m = (
            _GC_RATE_RE.search(record), _GC_HOURS_RE.search(record), _GC_AMOUNT_RE.search(record)
        )
        start, end = _gc_period_dates(m, default_year)
        extra: dict = {}
        if start:
            extra["period_start"] = start.isoformat()
        if end:
            extra["period_end"] = end.isoformat()
        items.append(
            ParsedLineItem(
                contractor_name=name,
                hours=clean_number(hours_m.group(1)) if hours_m else None,
                rate=clean_number(rate_m.group(1)) if rate_m else None,
                amount=clean_number(amount_m.group(1)) if amount_m else None,
                extra=extra,
            )
        )
    return items


# --- OCR-text block parser --------------------------------------------------
_CONTACT_RE = re.compile(r"Contact\s*:?\s*([A-Za-z][A-Za-z .'\-]+)", re.IGNORECASE)
_NUM_LINE_RE = re.compile(r"^[\$]?\s*[\d,]+\.\d{2}$")


def parse_ocr_blocks(text: str, default_name: str | None) -> list[ParsedLineItem]:
    """Parse OCR'd tabular invoices where each cell lands on its own line:
        <description with date range>
        <hours>
        <rate>
        <amount>
    A description line (with an embedded date range) is followed by its numeric cells.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    items: list[ParsedLineItem] = []
    for i, line in enumerate(lines):
        if not re.search(_DATE_TOKEN, line) or not re.search(r"[A-Za-z]", line):
            continue
        nums: list[float] = []
        j = i + 1
        while j < len(lines) and len(nums) < 3 and _NUM_LINE_RE.match(lines[j]):
            nums.append(clean_number(lines[j]) or 0.0)
            j += 1
        if len(nums) < 3:
            continue
        hours, rate, amount = nums[0], nums[1], nums[2]
        ps, pe = _line_period(line, None, None)
        extra: dict = {}
        if ps:
            extra["period_start"] = ps.isoformat()
        if pe:
            extra["period_end"] = pe.isoformat()
        items.append(
            ParsedLineItem(contractor_name=default_name or "Unknown", hours=hours, rate=rate,
                           amount=amount, extra=extra)
        )
    return items


def parse_from_text(text: str) -> RulesResult:
    """Build a RulesResult from raw text only (used for OCR output — no pdfplumber tables)."""
    warnings: list[str] = ["Parsed via OCR (scanned PDF)."]
    header = extract_header(text)
    contact = _CONTACT_RE.search(text)
    contact_name = contact.group(1).strip() if contact else None

    items = parse_rate_list_text(text) or parse_ocr_blocks(text, contact_name)
    total = header["total_invoice_cost"]
    if total is None and items:
        s = sum((li.amount or 0) for li in items)
        if s:
            total = round(s, 2)

    parsed = ParsedInvoice(
        vendor_name=header["vendor_name"],
        invoice_number=header["invoice_number"],
        date_received=header["date_received"],
        payment_period=header["payment_period"],
        payment_period_labeled=header["payment_period_labeled"],
        total_invoice_cost=total,
        line_items=items,
        contractor_name=contact_name or (items[0].contractor_name if items else None),
    )
    if items:
        parsed.hourly_or_fixed_rate = items[0].rate
        parsed.hours_worked = items[0].hours
    return RulesResult(parsed, confidence=_score(parsed, warnings), warnings=warnings, text=text, has_text=True)


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
    # Global Compass: per-line PAY PERIOD + "Hours- Name- $rate/hr  N hours  $amount". Dedicated parser
    # keeps each contractor's period/hours/rate/amount aligned (the generic rate-list parser mis-zips it).
    if not items and re.search(r"global\s+compass", text, re.IGNORECASE):
        items = parse_global_compass(text)
    # Fallback for other text-layout rate-list invoices (no real table).
    if not items:
        items = parse_rate_list_text(text)
    # Sogeti/Capgemini "Name ...Billable N Hours @ rate" text lines (table extractor reads nothing).
    if not items and re.search(r"\.{2,}\s*Billable\b", text, re.IGNORECASE):
        items = parse_billable_lines(text)
    # Odyssey "Qty Item Rate Amount" invoices where the data row is plain text under the header.
    if not items:
        items = parse_qty_item_lines(text)
    # NextStep Recruiting & same-shape "DESCRIPTION QTY RATE AMOUNT" invoices: the contractor name
    # (+ worked period in parens) sits under DESCRIPTION and the hours under QTY; rows are text, not a
    # ruled table, so the table extractor reads only the header.
    if not items:
        items = parse_desc_qty_rate_amount(text)
    # Cognizant text-row line items ("<Name> Onsite RTIME <hours> MHR <rate> <amount>"). Gated on the
    # vendor so the loose row pattern can't misfire on other invoices.
    if not items and re.search(r"cognizant", text, re.IGNORECASE):
        items = parse_cognizant_lines(text)
    # Multi-contractor "Services Rendered for:" billing (Gravity IT) where standard table parsing only
    # catches one row — use it when it recovers more contractors.
    if "services rendered for" in text.lower():
        sr_items = parse_services_rendered(tables)
        if len(sr_items) > len(items):
            items = sr_items
    warnings += item_warnings

    total = header["total_invoice_cost"]
    # If the printed total wasn't matched, fall back to the sum of line-item amounts.
    if total is None and items:
        s = sum((li.amount or 0) for li in items)
        if s:
            total = round(s, 2)

    parsed = ParsedInvoice(
        vendor_name=header["vendor_name"],
        invoice_number=header["invoice_number"],
        date_received=header["date_received"],
        payment_period=header["payment_period"],
        payment_period_labeled=header["payment_period_labeled"],
        total_invoice_cost=total,
        line_items=items,
    )
    # First contractor + their rate/hours surface to the top-level single-contractor fields.
    if items:
        parsed.contractor_name = items[0].contractor_name
        parsed.hourly_or_fixed_rate = items[0].rate
        parsed.hours_worked = items[0].hours

    confidence = _score(parsed, warnings)
    return RulesResult(parsed, confidence=confidence, warnings=warnings, text=text, has_text=True, tables=tables)


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
