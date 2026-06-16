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
    hourly_or_fixed_rate: float | None = None
    hours_worked: float | None = None
    total_invoice_cost: float | None = None
    line_items: list[ParsedLineItem] = []


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
    is_time_off: bool = False
    is_posted: bool = True
    included: bool = True  # counted toward the billable total (posted & not time-off)


class ClarityProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: str | None = None
    project_name: str | None = None
    budget_id: str | None = None
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
