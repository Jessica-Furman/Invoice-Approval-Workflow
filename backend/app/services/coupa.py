"""Coupa import-CSV generation for matched contractor invoices.

Turns a matched `Invoice` (+ its line items + linked Clarity data) into a Coupa-ready import CSV.
The CSV uses the **simplified MVP column subset** from `documentation/csv_rules` (not the full
~180-column Coupa template). Fields we can't source yet — accounting codes and the approval-chain
requester — are emitted as obvious **placeholder tokens** (e.g. ``<<CHART_OF_ACCOUNTS>>``) so a human
can spot and fill them in the downloaded file. As real mappings arrive (project export,
vendor->supplier-number, project->manager), replace the placeholder lookups in `_PLACEHOLDER` /
the `*_for` helpers with the actual source.

Structure of the emitted file (mirrors `documentation/Final CSV.txt`):
    row 1  -> Invoice header column schema
    row 2  -> Invoice Line column schema
    row 3  -> the invoice's header data row
    row 4+ -> one Invoice Line data row per contractor line item

`Account Allocation` rows are intentionally not emitted — they're only needed to split one line
across multiple accounts, which the MVP doesn't do.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import REPO_ROOT
from app.services.matching import _line_period

# --- Column schemas (per documentation/CSV creation blueprint.csv) -------------------------------

INVOICE_HEADER_COLUMNS = [
    "Invoice", "Invoice Number", "Supplier Number", "Supplier Name", "Status", "Invoice Date",
    "Submit For Approval?", "Line Level Taxation", "Chart of Accounts", "Currency",
    "Requester Email", "Requester Name", "Payment Terms", "Supplier Note", "Image Scan Url",
    "Local Currency Net", "Taxes In Origin Country Currency",
]

INVOICE_LINE_COLUMNS = [
    "Invoice Line", "Invoice Number", "Supplier Number", "Supplier Name", "Line Number",
    "Description", "Price", "Quantity", "Unit of Measure", "Category", "PO Number",
    "PO Line Number", "Account Code", "Account Segment 1", "Account Segment 2",
    "Account Segment 3", "Account Segment 4", "Billing Notes",
]

ACCOUNT_ALLOCATION_COLUMNS = [
    "Account Allocation", "Invoice Number", "Invoice Line Number", "Amount", "Percent",
    "Account Code", "Account Segment 1", "Account Segment 2", "Account Segment 3",
    "Account Segment 4", "Budget Period Name",
]

# --- Accounting segment mappings (documentation/csv_rules) ---------------------------------------
# Account Segment 1 = company code, Segment 2 = cost center — both keyed on the contractor's company
# (RAC vs ACIMA). Segment 3 = the CapEx/OpEx GL code; Segment 4 = the CapEx/OpEx label.
COMPANY_CODE = {"RAC": "5", "ACIMA": "67"}
COST_CENTER = {"RAC": "H0003", "ACIMA": "AC000"}
CAPEX_OPEX_CODE = {"CAPEX": "246010", "OPEX": "667070"}

# Company is resolved from the project's Line of Business in documentation/Company_by_Project.csv,
# keyed by Project ID. LOB "/Upbound" or "/Upbound/RAC" -> RAC; "/Upbound/Acima" -> ACIMA.
COMPANY_BY_PROJECT_CSV = REPO_ROOT / "documentation" / "Company_by_Project.csv"
_LOB_RAC = {"/upbound", "/upbound/rac"}
_LOB_ACIMA = {"/upbound/acima"}

# Fallback when a project ID isn't in the mapping: infer from the project name.
# \b avoids false hits like "tRACking"; "RACPad"/"RAConnect"/"RAC ..." all match \bRAC.
_RAC_RE = re.compile(r"\brac", re.IGNORECASE)
_ACIMA_RE = re.compile(r"\bacima", re.IGNORECASE)


def _load_project_company_map(path: Path) -> dict[str, str]:
    """Read Company_by_Project.csv into {Project ID -> 'RAC' | 'ACIMA'} via its Line of Business."""
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pid = (row.get("Project ID") or "").strip()
            lob = (row.get("Line of Business") or "").strip().lower()
            if not pid:
                continue
            if lob in _LOB_ACIMA:
                mapping[pid] = "ACIMA"
            elif lob in _LOB_RAC:
                mapping[pid] = "RAC"
    return mapping


@lru_cache(maxsize=1)
def _project_company_map() -> dict[str, str]:
    """Cached Project ID -> company lookup (loaded once from COMPANY_BY_PROJECT_CSV)."""
    return _load_project_company_map(COMPANY_BY_PROJECT_CSV)


def _load_project_lob_map(path: Path) -> dict[str, str]:
    """Read Company_by_Project.csv into {Project ID -> raw Line of Business string}."""
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pid = (row.get("Project ID") or "").strip()
            lob = (row.get("Line of Business") or "").strip()
            if pid and lob:
                mapping[pid] = lob
    return mapping


@lru_cache(maxsize=1)
def _project_lob_map() -> dict[str, str]:
    """Cached Project ID -> raw LOB string (e.g. '/Upbound/Acima')."""
    return _load_project_lob_map(COMPANY_BY_PROJECT_CSV)


def project_accounting(project_id: str | None, investment_name: str | None = None) -> dict[str, str | None]:
    """Accounting attributes for a project: its company, cost center, and raw Line of Business.

    Used to enrich the Excel Projects sheet. Company/cost center come from the same RAC/ACIMA rules the
    Coupa CSV uses; LOB is the raw string from Company_by_Project.csv.
    """
    company = _company_for_project(project_id, investment_name)
    return {
        "company": company,
        "cost_center": COST_CENTER.get(company),
        "lob": _project_lob_map().get(project_id) if project_id else None,
    }

# --- Placeholder tokens for data we can't source yet --------------------------------------------
# Swap each of these out for a real lookup (config/mapping table) once that data is available.
_PLACEHOLDER = {
    "supplier_number": "<<SUPPLIER_NUMBER>>",
    "chart_of_accounts": "<<CHART_OF_ACCOUNTS>>",
    "requester_email": "<<APPROVER_EMAIL>>",
    "requester_name": "<<APPROVER_NAME>>",
    "company_code": "<<COMPANY_CODE>>",
    "cost_center": "<<COST_CENTER>>",
    "capex_opex_code": "<<CAPEX_OPEX_CODE>>",
    "capex_opex_label": "<<CAPEX_OPEX>>",
}

# --- MVP header defaults (documentation/csv_rules "Recommended Header Defaults") -----------------
STATUS_DEFAULT = "draft"
CURRENCY_DEFAULT = "USD"
UNIT_OF_MEASURE = "HOUR"
CATEGORY_DEFAULT = "Contractor Services"
LINE_LEVEL_TAXATION = "no"
SUBMIT_FOR_APPROVAL = "no"  # per csv_rules: default to no until the workflow is trusted
# Chart of Accounts for a fully-matched invoice (no issues). Drafts/flagged keep the placeholder.
CHART_OF_ACCOUNTS_MATCHED = "321080-RT000"


def _fmt_date(d: date | None) -> str:
    """Coupa dates are MM/DD/YYYY (see Final CSV.txt)."""
    return d.strftime("%m/%d/%Y") if d else ""


def _fmt_money(n: float | None) -> str:
    return f"{n:.2f}" if n is not None else ""


def _fmt_num(n: float | None) -> str:
    """Hours: drop a pointless trailing .0 (40.0 -> 40) but keep real decimals (37.5)."""
    if n is None:
        return ""
    return str(int(n)) if float(n).is_integer() else str(n)


def _invoice_total(inv: models.Invoice) -> float:
    """Net/gross amount: the parsed invoice total, else the sum of line amounts."""
    if inv.total_invoice_cost is not None:
        return inv.total_invoice_cost
    return round(sum((li.amount or 0.0) for li in inv.line_items), 2)


def _project_for(li: models.InvoiceLineItem, db: Session | None) -> models.ClarityProject | None:
    """Look up the Clarity project behind a line's matched timesheet, if we have one."""
    ts = li.matched_clarity
    if ts is None or not ts.project_id or db is None:
        return None
    return db.scalars(
        select(models.ClarityProject).where(models.ClarityProject.project_id == ts.project_id)
    ).first()


def _company_for_project(project_id: str | None, investment_name: str | None) -> str | None:
    """Resolve a project's company ('RAC' | 'ACIMA').

    Primary: the project's Line of Business in Company_by_Project.csv, keyed by Project ID.
    Fallback: infer from the project name. None when neither resolves (caller emits a placeholder).
    """
    if project_id:
        company = _project_company_map().get(project_id)
        if company:
            return company
    name = investment_name or ""
    if _ACIMA_RE.search(name):
        return "ACIMA"
    if _RAC_RE.search(name):
        return "RAC"
    return None


def _norm_capex(val: str | None) -> str | None:
    """Normalize a CapEx/OpEx value to 'CAPEX' | 'OPEX', else None."""
    if val:
        v = val.strip().upper()
        if v in CAPEX_OPEX_CODE:
            return v
    return None


def _company_for(li: models.InvoiceLineItem) -> str | None:
    """The company for a line, from its matched Clarity timesheet's project (see _company_for_project)."""
    ts = li.matched_clarity
    if ts is None:
        return None
    return _company_for_project(ts.project_id, ts.investment_name)


def _capex_opex_for(
    li: models.InvoiceLineItem, project: models.ClarityProject | None
) -> str | None:
    """The line's CapEx/OpEx classification ('CAPEX' | 'OPEX'), from Clarity, else None."""
    ts = li.matched_clarity
    return _norm_capex((ts.capex_opex if ts else None) or (project.capex_opex if project else None))


def _segment_values(company: str | None, capex_opex: str | None) -> dict[str, str]:
    """The four Account Segment values for a (company, CapEx/OpEx) pair, with placeholders for gaps."""
    return {
        "Account Segment 1": COMPANY_CODE.get(company, _PLACEHOLDER["company_code"]),
        "Account Segment 2": COST_CENTER.get(company, _PLACEHOLDER["cost_center"]),
        "Account Segment 3": CAPEX_OPEX_CODE.get(capex_opex, _PLACEHOLDER["capex_opex_code"]),
        "Account Segment 4": capex_opex or _PLACEHOLDER["capex_opex_label"],
    }


def _clarity_company_breakdown(
    li: models.InvoiceLineItem, inv: models.Invoice, db: Session | None
) -> dict[tuple[str | None, str | None], float] | None:
    """Sum a matched contractor's in-period Clarity hours grouped by (company, CapEx/OpEx).

    Uses the same filter as matching — posted, not time-off, Date Worked within the line's period —
    so the buckets sum to the matched hours. Returns None when it can't be computed (no db / no
    matched Clarity row), so the caller falls back to a single invoice-hours line.
    """
    ts = li.matched_clarity
    if db is None or ts is None or not ts.contractor_name_normalized:
        return None
    start, end = _line_period(li, inv)
    q = select(models.ClarityTimesheet).where(
        models.ClarityTimesheet.contractor_name_normalized == ts.contractor_name_normalized,
        models.ClarityTimesheet.is_posted.is_(True),
        models.ClarityTimesheet.is_time_off.is_(False),
    )
    if start and end:
        q = q.where(
            models.ClarityTimesheet.date_worked >= start,
            models.ClarityTimesheet.date_worked <= end,
        )
    groups: dict[tuple[str | None, str | None], float] = {}
    for e in db.scalars(q).all():
        key = (_company_for_project(e.project_id, e.investment_name), _norm_capex(e.capex_opex))
        groups[key] = groups.get(key, 0.0) + (e.hours or 0.0)
    groups = {k: round(v, 2) for k, v in groups.items() if v}
    return groups or None


def _line_description(li: models.InvoiceLineItem, inv: models.Invoice) -> str:
    """'Contractor — Project — start-end' (the user-chosen line description shape).

    Project name comes from the matched Clarity timesheet's investment; omitted if unknown.
    Period falls back to the invoice period when the line carries no per-line dates.
    """
    name = li.contractor_name or "Contractor"
    start, end = _line_period(li, inv)
    parts = [name]
    project = li.matched_clarity.investment_name if li.matched_clarity else None
    if project:
        parts.append(project)
    if start and end:
        parts.append(f"{_fmt_date(start)}-{_fmt_date(end)}")
    return " - ".join(parts)  # ASCII separator — keep the whole CSV ASCII-safe for Coupa import


def build_header_row(inv: models.Invoice, *, matched_only: bool = False) -> dict[str, str]:
    """The single `Invoice` header data row, keyed by column name.

    A fully-matched invoice gets the real Chart of Accounts; a draft (flagged invoice, matched lines
    only) keeps the placeholder since it isn't a clean match.
    """
    total = _invoice_total(inv)
    matched = sum(1 for li in inv.line_items if li.line_status == models.STATUS_MATCHED)
    is_clean_match = inv.status == models.STATUS_MATCHED
    note = (
        f"Automated Clarity match: {inv.status}; {matched}/{len(inv.line_items)} line(s) matched."
        + (" Draft: matched contractors only." if matched_only else "")
    )
    chart = CHART_OF_ACCOUNTS_MATCHED if is_clean_match else _PLACEHOLDER["chart_of_accounts"]
    return {
        "Invoice": "Invoice",
        "Invoice Number": inv.invoice_number or "",
        "Supplier Number": _PLACEHOLDER["supplier_number"],
        "Supplier Name": inv.vendor_name or "",
        "Status": STATUS_DEFAULT,
        "Invoice Date": _fmt_date(inv.date_received),
        "Submit For Approval?": SUBMIT_FOR_APPROVAL,
        "Line Level Taxation": LINE_LEVEL_TAXATION,
        "Chart of Accounts": chart,
        "Currency": CURRENCY_DEFAULT,
        "Requester Email": _PLACEHOLDER["requester_email"],
        "Requester Name": _PLACEHOLDER["requester_name"],
        "Payment Terms": "",
        "Supplier Note": note,
        "Image Scan Url": "",                             # invoice-PDF S3 URL — added in a later phase
        "Local Currency Net": _fmt_money(total),          # net == gross (no tax, MVP rule)
        "Taxes In Origin Country Currency": "0.00",
    }


def _line_row(
    inv: models.Invoice, li: models.InvoiceLineItem, line_no: int, *,
    hours: float | None, description: str, segments: dict[str, str], billing: str,
) -> dict[str, str]:
    """Assemble one `Invoice Line` row. Price is the invoice rate; Amount = hours x rate."""
    amount = round(hours * li.rate, 2) if hours is not None and li.rate is not None else None
    return {
        "Invoice Line": "Invoice Line",
        "Invoice Number": inv.invoice_number or "",
        "Supplier Number": _PLACEHOLDER["supplier_number"],
        "Supplier Name": inv.vendor_name or "",
        "Line Number": str(line_no),
        "Description": description,
        "Price": _fmt_money(li.rate),
        "Quantity": _fmt_num(hours),
        "Unit of Measure": UNIT_OF_MEASURE,
        "Category": CATEGORY_DEFAULT,
        "PO Number": "",
        "PO Line Number": "",
        "Account Code": "",
        **segments,
        "Billing Notes": billing,
    }


def build_line_rows(
    inv: models.Invoice, db: Session | None = None, *, matched_only: bool = False
) -> list[dict[str, str]]:
    """`Invoice Line` rows for the invoice.

    Normally one row per contractor line item. But when a contractor's matched Clarity hours span
    more than one (company, CapEx/OpEx) bucket, that line is SPLIT into one row per bucket — each with
    that bucket's Clarity hours and its own company code / cost center / CapEx-OpEx segments — so RAC
    and ACIMA (and CapEx vs OpEx) work is coded separately for Coupa.

    With `matched_only=True` (draft CSV for a flagged invoice), only contractors that matched Clarity
    get lines; unmatched contractors are skipped for the user to fill in by hand.
    """
    rows: list[dict[str, str]] = []
    line_no = 1
    for li in inv.line_items:
        if matched_only and li.line_status != models.STATUS_MATCHED:
            continue
        breakdown = _clarity_company_breakdown(li, inv, db)

        if breakdown and len(breakdown) > 1:
            start, end = _line_period(li, inv)
            period = f"{_fmt_date(start)}-{_fmt_date(end)}" if start and end else ""
            name = li.contractor_name or "Contractor"
            # Stable order: RAC before ACIMA before unknown, then CAPEX before OPEX.
            for (company, capex_opex), hours in sorted(
                breakdown.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))
            ):
                label = " ".join(p for p in (company, capex_opex) if p) or "unclassified"
                desc = " - ".join(p for p in (name, label, period) if p)
                billing = f"Clarity {_fmt_num(hours)}h posted on {label} project(s); split line"
                rows.append(
                    _line_row(inv, li, line_no, hours=hours, description=desc,
                              segments=_segment_values(company, capex_opex), billing=billing)
                )
                line_no += 1
            continue

        # Single bucket (or no Clarity breakdown): one line using the invoice's own hours.
        project = _project_for(li, db)
        segments = _segment_values(_company_for(li), _capex_opex_for(li, project))
        clarity_hours = None
        if li.diff and isinstance(li.diff, dict):
            v = li.diff.get("clarity_hours")
            clarity_hours = v if isinstance(v, (int, float)) else None
        billing = (
            f"Clarity {_fmt_num(clarity_hours)}h posted; line {li.line_status or 'n/a'}"
            if clarity_hours is not None
            else f"Line {li.line_status or 'n/a'}"
        )
        rows.append(
            _line_row(inv, li, line_no, hours=li.hours, description=_line_description(li, inv),
                      segments=segments, billing=billing)
        )
        line_no += 1
    return rows


def coupa_csv_bytes(
    inv: models.Invoice, db: Session | None = None, *, matched_only: bool = False
) -> bytes:
    """Render the Coupa import CSV for one invoice as UTF-8 bytes (BOM for Excel/Coupa).

    `matched_only=True` produces a DRAFT for a flagged invoice: only matched contractors get lines.
    """
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)

    # Two column-schema rows up top, exactly like documentation/Final CSV.txt.
    writer.writerow(INVOICE_HEADER_COLUMNS)
    writer.writerow(INVOICE_LINE_COLUMNS)

    header = build_header_row(inv, matched_only=matched_only)
    writer.writerow([header[c] for c in INVOICE_HEADER_COLUMNS])
    for row in build_line_rows(inv, db, matched_only=matched_only):
        writer.writerow([row[c] for c in INVOICE_LINE_COLUMNS])

    return buf.getvalue().encode("utf-8-sig")


def _safe_filename_part(s: str) -> str:
    """Make a string safe to drop into a download filename: strip characters Windows/most OSes
    reject (\\ / : * ? \" < > |), collapse whitespace, and trim trailing dots/spaces."""
    s = re.sub(r'[\\/:*?"<>|]', "", s)
    s = re.sub(r"\s+", " ", s).strip().strip(".")
    return s


def coupa_csv_filename(inv: models.Invoice, *, draft: bool = False) -> str:
    """'<vendor name>_<invoice number>.csv' so each download is easy to tie back to its invoice.

    Draft (flagged, matched-only) downloads are prefixed 'DRAFT_' to keep them distinct.
    """
    vendor = _safe_filename_part(inv.vendor_name or "")
    number = _safe_filename_part(inv.invoice_number or str(inv.id))
    name = "_".join(p for p in (vendor, number) if p) or f"coupa_{inv.id}"
    return f"{'DRAFT_' if draft else ''}{name}.csv"
