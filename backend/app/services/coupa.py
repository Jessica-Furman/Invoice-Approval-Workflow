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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
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

# Company is inferred from the Clarity project name (no LOB/company field in the export yet).
# \b avoids false hits like "tRACking"; "RACPad"/"RAConnect"/"RAC ..." all match \bRAC.
_RAC_RE = re.compile(r"\brac", re.IGNORECASE)
_ACIMA_RE = re.compile(r"\bacima", re.IGNORECASE)

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


def _company_for(li: models.InvoiceLineItem) -> str | None:
    """Infer the contractor's company ('RAC' | 'ACIMA') from the matched project name.

    Returns None when the name carries no signal — caller then emits a placeholder rather than
    guessing a company code. This is the swap point for a real contractor/project->company mapping.
    """
    name = (li.matched_clarity.investment_name if li.matched_clarity else None) or ""
    if _ACIMA_RE.search(name):
        return "ACIMA"
    if _RAC_RE.search(name):
        return "RAC"
    return None


def _capex_opex_for(
    li: models.InvoiceLineItem, project: models.ClarityProject | None
) -> str | None:
    """The line's CapEx/OpEx classification ('CAPEX' | 'OPEX'), from Clarity, else None."""
    ts = li.matched_clarity
    val = (ts.capex_opex if ts else None) or (project.capex_opex if project else None)
    if val:
        v = val.strip().upper()
        if v in CAPEX_OPEX_CODE:
            return v
    return None


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


def build_header_row(inv: models.Invoice) -> dict[str, str]:
    """The single `Invoice` header data row, keyed by column name."""
    total = _invoice_total(inv)
    matched = sum(1 for li in inv.line_items if li.line_status == models.STATUS_MATCHED)
    note = (
        f"Automated Clarity match: {inv.status}; "
        f"{matched}/{len(inv.line_items)} line(s) matched."
    )
    return {
        "Invoice": "Invoice",
        "Invoice Number": inv.invoice_number or "",
        "Supplier Number": _PLACEHOLDER["supplier_number"],
        "Supplier Name": inv.vendor_name or "",
        "Status": STATUS_DEFAULT,
        "Invoice Date": _fmt_date(inv.date_received),
        "Submit For Approval?": SUBMIT_FOR_APPROVAL,
        "Line Level Taxation": LINE_LEVEL_TAXATION,
        "Chart of Accounts": _PLACEHOLDER["chart_of_accounts"],
        "Currency": CURRENCY_DEFAULT,
        "Requester Email": _PLACEHOLDER["requester_email"],
        "Requester Name": _PLACEHOLDER["requester_name"],
        "Payment Terms": "",
        "Supplier Note": note,
        "Image Scan Url": "",                             # invoice-PDF S3 URL — added in a later phase
        "Local Currency Net": _fmt_money(total),          # net == gross (no tax, MVP rule)
        "Taxes In Origin Country Currency": "0.00",
    }


def build_line_rows(inv: models.Invoice, db: Session | None = None) -> list[dict[str, str]]:
    """One `Invoice Line` data row per contractor line item, keyed by column name."""
    rows: list[dict[str, str]] = []
    for n, li in enumerate(inv.line_items, start=1):
        project = _project_for(li, db)
        company = _company_for(li)                    # 'RAC' | 'ACIMA' | None
        capex_opex = _capex_opex_for(li, project)     # 'CAPEX' | 'OPEX' | None

        seg1 = COMPANY_CODE.get(company, _PLACEHOLDER["company_code"])   # company code (5 / 67)
        seg2 = COST_CENTER.get(company, _PLACEHOLDER["cost_center"])     # cost center (H0003 / AC000)
        seg3 = CAPEX_OPEX_CODE.get(capex_opex, _PLACEHOLDER["capex_opex_code"])  # GL code
        seg4 = capex_opex or _PLACEHOLDER["capex_opex_label"]            # CAPEX / OPEX label

        clarity_hours = None
        if li.diff and isinstance(li.diff, dict):
            v = li.diff.get("clarity_hours")
            clarity_hours = v if isinstance(v, (int, float)) else None
        billing = (
            f"Clarity {_fmt_num(clarity_hours)}h posted; line {li.line_status or 'n/a'}"
            if clarity_hours is not None
            else f"Line {li.line_status or 'n/a'}"
        )
        rows.append({
            "Invoice Line": "Invoice Line",
            "Invoice Number": inv.invoice_number or "",
            "Supplier Number": _PLACEHOLDER["supplier_number"],
            "Supplier Name": inv.vendor_name or "",
            "Line Number": str(n),
            "Description": _line_description(li, inv),
            "Price": _fmt_money(li.rate),
            "Quantity": _fmt_num(li.hours),
            "Unit of Measure": UNIT_OF_MEASURE,
            "Category": CATEGORY_DEFAULT,
            "PO Number": "",
            "PO Line Number": "",
            "Account Code": "",
            "Account Segment 1": seg1,
            "Account Segment 2": seg2,
            "Account Segment 3": seg3,
            "Account Segment 4": seg4,
            "Billing Notes": billing,
        })
    return rows


def coupa_csv_bytes(inv: models.Invoice, db: Session | None = None) -> bytes:
    """Render the full Coupa import CSV for one invoice as UTF-8 bytes (BOM for Excel/Coupa)."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)

    # Two column-schema rows up top, exactly like documentation/Final CSV.txt.
    writer.writerow(INVOICE_HEADER_COLUMNS)
    writer.writerow(INVOICE_LINE_COLUMNS)

    header = build_header_row(inv)
    writer.writerow([header[c] for c in INVOICE_HEADER_COLUMNS])
    for row in build_line_rows(inv, db):
        writer.writerow([row[c] for c in INVOICE_LINE_COLUMNS])

    return buf.getvalue().encode("utf-8-sig")


def coupa_csv_filename(inv: models.Invoice) -> str:
    return f"coupa_{inv.invoice_number or inv.id}.csv"
