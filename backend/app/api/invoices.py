"""Invoice + dashboard API routes."""
from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db.base import get_db
from app.services.coupa import coupa_csv_bytes, coupa_csv_filename, project_accounting
from app.services.export_excel import workbook_from_detail
from app.services.ingestion import ingest_pdf
from app.services.storage import LocalStorage
from app.services.matching import (
    ClarityIndex,
    _counts_toward_billable,
    _line_period,
    countable_status_filter,
    match_all,
    match_invoice,
)
from app.services.routing import remove_from_inboxes, route_all, route_invoice
from app.schemas import (
    ClarityEntryOut,
    ClarityProjectOut,
    ClarityTimesheetOut,
    DashboardResponse,
    InvoiceDetail,
    InvoiceSummary,
    LineItemOut,
    MismatchReason,
    UploadResult,
    UploadResultItem,
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
        archived_at=inv.archived_at,
        line_item_count=len(line_items),
        matched_line_count=matched,
        parse_method=(inv.raw_extraction or {}).get("method"),
    )


@router.post("/invoices/upload", response_model=UploadResult)
async def upload_invoices(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
) -> UploadResult:
    """Upload one or more contractor invoice PDFs, then parse + match + route each.

    Runs the same pipeline the CLI does (`ingest_pdf` -> `match_invoice` -> `route_invoice`),
    so an uploaded invoice lands on the dashboard exactly like the bundled samples. The Clarity
    index is built once and reused across the batch.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    storage = LocalStorage(settings.STORAGE_DIR)
    index = ClarityIndex.build(db)
    results: list[UploadResultItem] = []

    for upload in files:
        name = upload.filename or "invoice.pdf"
        if not name.lower().endswith(".pdf"):
            results.append(UploadResultItem(filename=name, ok=False, error="Not a PDF"))
            continue
        # Preserve the original filename in a temp dir so ingest's stem fallback (used when no
        # invoice number is parsed) stays meaningful.
        tmp_dir = Path(tempfile.mkdtemp(prefix="invoicee_upload_"))
        tmp_path = tmp_dir / Path(name).name
        try:
            with tmp_path.open("wb") as out:
                shutil.copyfileobj(upload.file, out)
            inv = ingest_pdf(db, str(tmp_path), storage=storage)
            match_invoice(db, inv, index)
            route_invoice(db, inv)
            db.commit()
            db.refresh(inv)
            results.append(
                UploadResultItem(
                    filename=name,
                    ok=True,
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    status=inv.status,
                )
            )
        except Exception as e:  # noqa: BLE001 — surface per-file failures, keep batch going
            db.rollback()
            results.append(UploadResultItem(filename=name, ok=False, error=str(e)))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return UploadResult(
        uploaded=sum(1 for r in results if r.ok),
        failed=sum(1 for r in results if not r.ok),
        results=results,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    """Three-column board: Flagged | Matched | All (User Story 14).

    Excludes archived invoices (bulk-exported via the slider) — they live on in the History tab.
    """
    invoices = db.scalars(
        select(models.Invoice)
        .where(
            models.Invoice.archived_at.is_(None),
            models.Invoice.invoice_type == models.INVOICE_TYPE_CONTRACTOR,
        )
        .order_by(models.Invoice.created_at.desc())
    ).all()
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
            time_sheet_status=r.time_sheet_status,
            is_time_off=r.is_time_off,
            is_posted=r.is_posted,
            included=bool(_counts_toward_billable(r) and not r.is_time_off),  # Posted or Submitted
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


@router.post("/invoices/{invoice_id}/coupa.csv")
def generate_coupa_csv(invoice_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    """Build the Coupa import CSV for a MATCHED invoice and download it (User Stories 19-21).

    This is the manual "Approve & Create CSV" action — it only runs when the user clicks the button,
    never automatically. Only matched invoices are eligible; flagged/needs-review/failed invoices are
    blocked (US 21) and must go through manual review first. Generating the CSV stamps
    ``coupa_csv_generated_at`` and logs an audit event; the file itself is not routed anywhere yet.
    """
    inv = db.get(models.Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status != models.STATUS_MATCHED:
        raise HTTPException(
            status_code=409,
            detail="Only matched invoices can generate a Coupa CSV. Resolve the flags first.",
        )

    data = coupa_csv_bytes(inv, db)
    inv.coupa_csv_generated_at = datetime.utcnow()
    db.add(models.AuditLog(invoice_id=inv.id, event="coupa_csv_generated", detail={"bytes": len(data)}))
    db.commit()

    fname = coupa_csv_filename(inv)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/invoices/{invoice_id}/coupa-draft.csv")
def generate_coupa_draft_csv(invoice_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    """Build a DRAFT Coupa CSV for a flagged invoice — lines for the contractors that DID match only.

    Contractors that didn't match Clarity are omitted so the user can add those rows by hand. Works on
    any invoice that has at least one matched line (intended for flagged invoices); the Chart of
    Accounts stays a placeholder because the invoice isn't a clean match. Logs an audit event.
    """
    inv = db.get(models.Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    matched_lines = [li for li in inv.line_items if li.line_status == models.STATUS_MATCHED]
    if not matched_lines:
        raise HTTPException(
            status_code=409,
            detail="No matched contractors on this invoice — nothing to draft.",
        )

    data = coupa_csv_bytes(inv, db, matched_only=True)
    db.add(models.AuditLog(
        invoice_id=inv.id, event="coupa_draft_csv_generated",
        detail={"matched_lines": len(matched_lines), "bytes": len(data)},
    ))
    db.commit()

    fname = coupa_csv_filename(inv, draft=True)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/invoices/bulk-export-matched")
def bulk_export_matched(db: Session = Depends(get_db)) -> StreamingResponse:
    """Generate a Coupa CSV for EVERY active matched invoice, then archive them (clear from the board).

    Returns a single ZIP containing one separate CSV per invoice. Archiving hides the invoices from
    the dashboard but keeps them in the DB (visible in History) — nothing is deleted. Powers the
    "Export All" slider on the Matched column.
    """
    invoices = db.scalars(
        select(models.Invoice)
        .where(
            models.Invoice.status == models.STATUS_MATCHED,
            models.Invoice.archived_at.is_(None),
            models.Invoice.invoice_type == models.INVOICE_TYPE_CONTRACTOR,
        )
        .order_by(models.Invoice.created_at.desc())
    ).all()
    if not invoices:
        raise HTTPException(status_code=409, detail="No matched invoices to export.")

    now = datetime.utcnow()
    buf = io.BytesIO()
    used_names: set[str] = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for inv in invoices:
            name = coupa_csv_filename(inv)
            if name in used_names:  # guard against two invoices producing the same filename
                name = f"{name[:-4]}_{inv.id}.csv"
            used_names.add(name)
            zf.writestr(name, coupa_csv_bytes(inv, db))
            inv.coupa_csv_generated_at = now
            inv.archived_at = now
            db.add(models.AuditLog(invoice_id=inv.id, event="bulk_exported", detail={"file": name}))
    db.commit()

    buf.seek(0)
    fname = f"coupa_export_{now:%Y%m%d_%H%M%S}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/history", response_model=list[InvoiceSummary])
def history(db: Session = Depends(get_db)) -> list[InvoiceSummary]:
    """Every invoice still in the DB — active and archived (bulk-exported) — newest first.

    This is the permanent record so the user can check whether an invoice was already processed.
    Deleted invoices are gone from the DB, so they don't appear. Re-uploads reuse the same row
    (idempotent on invoice number), so the same invoice never appears twice.
    """
    invoices = db.scalars(
        select(models.Invoice)
        .where(models.Invoice.invoice_type == models.INVOICE_TYPE_CONTRACTOR)
        .order_by(models.Invoice.created_at.desc())
    ).all()
    return [_summary(i) for i in invoices]


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


@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)) -> dict:
    """Permanently delete an invoice: its line items, audit log, mock-inbox copies, and stored PDF.

    Used by the UI's per-invoice Delete action (with a confirmation prompt). Idempotent enough that a
    missing invoice returns 404; everything tied to the invoice is removed so it disappears from the board.
    """
    inv = db.get(models.Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    key = inv.pdf_storage_key
    remove_from_inboxes(inv)                      # mock Outlook inboxes (matched/flagged)
    if key:
        LocalStorage(settings.STORAGE_DIR).delete(key)  # mock S3
    db.execute(delete(models.AuditLog).where(models.AuditLog.invoice_id == invoice_id))
    db.delete(inv)                                # cascades line items
    db.commit()
    return {"deleted": invoice_id, "invoice_number": inv.invoice_number}


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
            countable_status_filter(),  # Posted OR Submitted
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

    # Enrich each project with the accounting fields the Excel export shows: cost center + LOB from the
    # project->company mapping (same rules as the Coupa CSV), and vendor from the invoice itself.
    project_outs: list[ClarityProjectOut] = []
    for p in projects:
        acct = project_accounting(p.project_id, p.project_name)
        out = ClarityProjectOut.model_validate(p)
        out.cost_code = acct["cost_code"]   # company code: RAC -> 5, ACIMA -> 67
        out.cost_center = acct["cost_center"] or p.cost_center
        out.lob = acct["lob"] or p.lob
        out.vendor = inv.vendor_name or p.vendor
        project_outs.append(out)

    base = _summary(inv)
    return InvoiceDetail(
        **base.model_dump(),
        mismatch_reasons=[MismatchReason(**m) for m in (inv.mismatch_reasons or [])],
        pdf_storage_key=inv.pdf_storage_key,
        parse_confidence=inv.parse_confidence,
        coupa_csv_generated_at=inv.coupa_csv_generated_at,
        line_items=[LineItemOut.model_validate(li) for li in line_items],
        clarity_timesheets=timesheets,
        clarity_projects=project_outs,
    )
