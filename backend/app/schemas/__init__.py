"""Pydantic schemas: API DTOs and the parsed-invoice JSON contract."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Parsed-invoice contract (User Story 2). The line-item portion is versioned
# and treated as evolvable per product guidance.
# ---------------------------------------------------------------------------
class ParsedLineItem(BaseModel):
    contractor_name: str | None = None
    hours: float | None = None
    rate: float | None = None
    amount: float | None = None
    extra: dict = {}


class ParsedInvoice(BaseModel):
    schema_version: int = 1
    vendor_name: str | None = None
    contractor_name: str | None = None  # primary/first contractor (single-contractor invoices)
    invoice_number: str | None = None
    date_received: date | None = None
    payment_period: str | None = None
    payment_period_labeled: bool = False  # True if found next to a "Period:" label (authoritative)
    hourly_or_fixed_rate: float | None = None
    hours_worked: float | None = None
    total_invoice_cost: float | None = None
    line_items: list[ParsedLineItem] = []


# ---------------------------------------------------------------------------
# "Other Invoice Types" contract (hardware / software / subscription). No Clarity
# matching — we simply extract the vendor's service lines. "description" is the
# SERVICE billed (not a person). Quantity/unit price are optional.
# ---------------------------------------------------------------------------
class ParsedOtherLineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class ParsedOtherInvoice(BaseModel):
    schema_version: int = 1
    vendor_name: str | None = None
    invoice_number: str | None = None
    date_received: date | None = None
    total_invoice_cost: float | None = None
    line_items: list[ParsedOtherLineItem] = []


# ---------------------------------------------------------------------------
# API response DTOs
# ---------------------------------------------------------------------------
class MismatchReason(BaseModel):
    field: str
    reason: str
    invoice_value: str | None = None
    clarity_value: str | None = None


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contractor_name: str | None = None
    hours: float | None = None
    rate: float | None = None
    amount: float | None = None
    line_status: str | None = None
    diff: dict | None = None
    matched_clarity_id: int | None = None


class ClarityTimesheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contractor_name: str | None = None
    hours: float | None = None
    rate: float | None = None
    period_start: date | None = None
    period_end: date | None = None
    project_id: str | None = None
    investment_name: str | None = None
    investment_manager: str | None = None
    resource_manager: str | None = None


class ClarityEntryOut(BaseModel):
    """A single date-level Clarity time entry — the drill-down behind a summed contractor total."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date_worked: date | None = None
    hours: float | None = None
    project_id: str | None = None
    investment_name: str | None = None
    task_name: str | None = None
    time_sheet_status: str | None = None  # raw Clarity status: Posted / Submitted / Open / Approved / …
    is_time_off: bool = False
    is_posted: bool = True
    included: bool = True  # counted toward the billable total (posted & not time-off)


class ClarityProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: str | None = None
    project_name: str | None = None
    budget_id: str | None = None
    cost_code: str | None = None       # company code: RAC -> 5, ACIMA -> 67
    capex_opex: str | None = None
    cost_center: str | None = None
    vendor: str | None = None
    lob: str | None = None
    spend: float | None = None


class InvoiceSummary(BaseModel):
    """Card view in the dashboard columns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_name: str | None = None
    invoice_number: str | None = None
    date_received: date | None = None
    payment_period_start: date | None = None
    payment_period_end: date | None = None
    total_invoice_cost: float | None = None
    status: str
    routed_to: str | None = None
    archived_at: datetime | None = None  # set when bulk-exported via the slider (hidden from board)
    line_item_count: int = 0
    matched_line_count: int = 0


class InvoiceDetail(InvoiceSummary):
    """Detail-drawer payload: invoice + line items + matching Clarity + projects (User Story 15)."""

    mismatch_reasons: list[MismatchReason] = []
    pdf_storage_key: str | None = None
    parse_confidence: float | None = None
    coupa_csv_generated_at: datetime | None = None
    line_items: list[LineItemOut] = []
    clarity_timesheets: list[ClarityTimesheetOut] = []
    clarity_projects: list[ClarityProjectOut] = []


class DashboardResponse(BaseModel):
    flagged: list[InvoiceSummary] = []
    matched: list[InvoiceSummary] = []
    all: list[InvoiceSummary] = []


class UploadResultItem(BaseModel):
    """Per-file outcome of an invoice upload batch."""

    filename: str
    ok: bool
    invoice_id: int | None = None
    invoice_number: str | None = None
    status: str | None = None
    error: str | None = None


class UploadResult(BaseModel):
    uploaded: int = 0
    failed: int = 0
    results: list[UploadResultItem] = []


# ---------------------------------------------------------------------------
# "Other Invoice Types" API DTOs (hardware / software / subscription board)
# ---------------------------------------------------------------------------
class OtherLineItemOut(BaseModel):
    """One parsed service line: description (service billed) + optional qty/unit price + amount."""

    id: int
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class OtherInvoiceSummary(BaseModel):
    """Card view on the Other-invoices board."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_name: str | None = None
    invoice_number: str | None = None
    date_received: date | None = None
    total_invoice_cost: float | None = None
    status: str  # all_data_found | missing_data
    supplier_number: str | None = None
    archived_at: datetime | None = None
    line_item_count: int = 0
    missing_count: int = 0


class OtherInvoiceDetail(OtherInvoiceSummary):
    """Detail-drawer payload: all parsed fields + the service line-item table + missing-field list."""

    pdf_storage_key: str | None = None
    parse_confidence: float | None = None
    missing_fields: list[str] = []
    line_items: list[OtherLineItemOut] = []


class OtherDashboardResponse(BaseModel):
    missing: list[OtherInvoiceSummary] = []
    found: list[OtherInvoiceSummary] = []
    all: list[OtherInvoiceSummary] = []
