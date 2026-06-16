"""Invoice + dashboard API routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db.base import get_db
from app.services.export_excel import workbook_from_detail
from app.services.storage import LocalStorage
from app.services.matching import ClarityIndex, _line_period, match_all, match_invoice
from app.services.routing import route_all, route_invoice
from app.schemas import (
    ClarityEntryOut,
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
        routed_to=inv.routed_to,
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


@router.get(
    "/invoices/{invoice_id}/lines/{line_item_id}/clarity-entries",
    response_model=list[ClarityEntryOut],
)
def line_clarity_breakdown(
    invoice_id: int, line_item_id: int, db: Session = Depends(get_db)
) -> list[ClarityEntryOut]:
    """Date-level Clarity entries behind a contractor's summed total — the drill-down for the UI.

    Shows every in-period entry for the matched contractor, flagging which ones were counted
    (posted & not time-off) vs excluded, so the user can see exactly how the total was built.
    """
    li = db.get(models.InvoiceLineItem, line_item_id)
    if li is None or li.invoice_id != invoice_id:
        raise HTTPException(status_code=404, detail="Line item not found")
    if li.matched_clarity is None:
        return []

    norm = li.matched_clarity.contractor_name_normalized
    inv = li.invoice
    start, end = _line_period(li, inv)

    q = select(models.ClarityTimesheet).where(
        models.ClarityTimesheet.contractor_name_normalized == norm
    )
    if start and end:
        q = q.where(
            models.ClarityTimesheet.date_worked >= start,
            models.ClarityTimesheet.date_worked <= end,
        )
    rows = db.scalars(q.order_by(models.ClarityTimesheet.date_worked)).all()

    return [
        ClarityEntryOut(
            id=r.id,
            date_worked=r.date_worked,
            hours=r.hours,
            project_id=r.project_id,
            investment_name=r.investment_name,
            task_name=r.task_name,
            is_time_off=r.is_time_off,
            is_posted=r.is_posted,
            included=bool(r.is_posted and not r.is_time_off),
        )
        for r in rows
    ]


@router.get("/invoices/{invoice_id}/pdf")
def get_invoice_pdf(invoice_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """Serve the original invoice PDF (inline so it opens in the browser viewer)."""
    inv = db.get(models.Invoice, invoice_id)
    if inv is None or not inv.pdf_storage_key:
        raise HTTPException(status_code=404, detail="No PDF for this invoice")
    storage = LocalStorage(settings.STORAGE_DIR)
    path = storage.path_for(inv.pdf_storage_key)
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail="PDF file missing from storage")
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{inv.pdf_storage_key}"'},
    )


@router.get("/invoices/{invoice_id}/export.xlsx")
def export_invoice_xlsx(invoice_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    """Download invoice + Clarity side-by-side + projects as an Excel workbook (User Story 19)."""
    detail = invoice_detail(invoice_id, db)
    buf = workbook_from_detail(detail)
    fname = f"invoice_{detail.invoice_number or invoice_id}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/match-all")
def run_match_all(db: Session = Depends(get_db)) -> dict:
    """Re-run name+hours matching across all invoices, then route them to matched/flagged inboxes."""
    counts = match_all(db)
    counts["routed"] = route_all(db)
    return counts


@router.post("/invoices/{invoice_id}/rematch", response_model=InvoiceDetail)
def rematch(invoice_id: int, db: Session = Depends(get_db)) -> InvoiceDetail:
    inv = db.get(models.Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    match_invoice(db, inv, ClarityIndex.build(db))
    route_invoice(db, inv)
    db.commit()
    return invoice_detail(invoice_id, db)


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
def invoice_detail(invoice_id: int, db: Session = Depends(get_db)) -> InvoiceDetail:
    """Detail drawer: invoice + line items + matching Clarity timesheets + projects (US 15)."""
    inv = db.get(models.Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    line_items = list(inv.line_items)

    # Show the Clarity rows that matching linked to this invoice: billable (non-time-off) entries
    # whose Date Worked falls in the invoice period, aggregated to one row per contractor.
    matched_norms = {
        li.matched_clarity.contractor_name_normalized
        for li in line_items
        if li.matched_clarity is not None
    }
    raw_rows: list[models.ClarityTimesheet] = []
    if matched_norms:
        ts_query = select(models.ClarityTimesheet).where(
            models.ClarityTimesheet.contractor_name_normalized.in_(matched_norms),
            models.ClarityTimesheet.is_time_off.is_(False),
            models.ClarityTimesheet.is_posted.is_(True),
        )
        if inv.payment_period_start and inv.payment_period_end:
            ts_query = ts_query.where(
                models.ClarityTimesheet.date_worked >= inv.payment_period_start,
                models.ClarityTimesheet.date_worked <= inv.payment_period_end,
            )
        raw_rows = list(db.scalars(ts_query).all())

    # Aggregate per contractor for the side-by-side display.
    agg: dict[str, ClarityTimesheetOut] = {}
    for r in raw_rows:
        key = r.contractor_name_normalized or str(r.id)
        if key not in agg:
            agg[key] = ClarityTimesheetOut(
                id=r.id, contractor_name=r.contractor_name, hours=0.0, rate=None,
                period_start=inv.payment_period_start, period_end=inv.payment_period_end,
                project_id=r.project_id, investment_name=r.investment_name,
                investment_manager=r.investment_manager, resource_manager=r.resource_manager,
            )
        agg[key].hours = round((agg[key].hours or 0) + (r.hours or 0), 2)
    timesheets = list(agg.values())

    # Related projects: from the matched timesheets' project ids.
    project_ids = {t.project_id for t in raw_rows if t.project_id}
    projects = (
        db.scalars(
            select(models.ClarityProject).where(models.ClarityProject.project_id.in_(project_ids))
        ).all()
        if project_ids
        else []
    )

    base = _summary(inv)
    return InvoiceDetail(
        **base.model_dump(),
        mismatch_reasons=[MismatchReason(**m) for m in (inv.mismatch_reasons or [])],
        pdf_storage_key=inv.pdf_storage_key,
        parse_confidence=inv.parse_confidence,
        coupa_csv_generated_at=inv.coupa_csv_generated_at,
        line_items=[LineItemOut.model_validate(li) for li in line_items],
        clarity_timesheets=timesheets,
        clarity_projects=[ClarityProjectOut.model_validate(p) for p in projects],
    )
