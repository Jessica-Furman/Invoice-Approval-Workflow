"""Invoice + dashboard API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.db.base import get_db
from app.schemas import (
    ClarityProjectOut,
    ClarityTimesheetOut,
    DashboardResponse,
    InvoiceDetail,
    InvoiceSummary,
    LineItemOut,
    MismatchReason,
)

router = APIRouter(prefix="/api", tags=["invoices"])


def _summary(inv: models.Invoice) -> InvoiceSummary:
    line_items = list(inv.line_items)
    matched = sum(1 for li in line_items if li.line_status == models.STATUS_MATCHED)
    return InvoiceSummary(
        id=inv.id,
        vendor_name=inv.vendor_name,
        invoice_number=inv.invoice_number,
        date_received=inv.date_received,
        payment_period_start=inv.payment_period_start,
        payment_period_end=inv.payment_period_end,
        total_invoice_cost=inv.total_invoice_cost,
        status=inv.status,
        line_item_count=len(line_items),
        matched_line_count=matched,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    """Three-column board: Flagged | Matched | All (User Story 14)."""
    invoices = db.scalars(select(models.Invoice).order_by(models.Invoice.created_at.desc())).all()
    summaries = [_summary(i) for i in invoices]
    return DashboardResponse(
        all=summaries,
        matched=[s for s in summaries if s.status == models.STATUS_MATCHED],
        flagged=[
            s
            for s in summaries
            if s.status in (models.STATUS_FLAGGED, models.STATUS_NEEDS_REVIEW, models.STATUS_FAILED)
        ],
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
def invoice_detail(invoice_id: int, db: Session = Depends(get_db)) -> InvoiceDetail:
    """Detail drawer: invoice + line items + matching Clarity timesheets + projects (US 15)."""
    inv = db.get(models.Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    line_items = list(inv.line_items)
    norm_names = {li.contractor_name_normalized for li in line_items if li.contractor_name_normalized}

    # Matching Clarity timesheets (by normalized contractor name for the MVP).
    timesheets = (
        db.scalars(
            select(models.ClarityTimesheet).where(
                models.ClarityTimesheet.contractor_name_normalized.in_(norm_names)
            )
        ).all()
        if norm_names
        else []
    )

    # Related projects: by this invoice's vendor or by the matched timesheets' project ids.
    project_ids = {t.project_id for t in timesheets if t.project_id}
    proj_query = select(models.ClarityProject).where(
        (models.ClarityProject.vendor == inv.vendor_name)
        | (models.ClarityProject.project_id.in_(project_ids) if project_ids else False)
    )
    projects = db.scalars(proj_query).all()

    base = _summary(inv)
    return InvoiceDetail(
        **base.model_dump(),
        mismatch_reasons=[MismatchReason(**m) for m in (inv.mismatch_reasons or [])],
        pdf_storage_key=inv.pdf_storage_key,
        parse_confidence=inv.parse_confidence,
        coupa_csv_generated_at=inv.coupa_csv_generated_at,
        line_items=[LineItemOut.model_validate(li) for li in line_items],
        clarity_timesheets=[ClarityTimesheetOut.model_validate(t) for t in timesheets],
        clarity_projects=[ClarityProjectOut.model_validate(p) for p in projects],
    )
