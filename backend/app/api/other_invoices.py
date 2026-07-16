"""API routes for the **Other Invoice Types** board (hardware / software / subscription).

Fully separate from the contractor routes: uploads here run ONLY the `parse_other_invoice` rules
(never contractor parsing), and there is no Clarity matching or Coupa export. The generic
`GET /api/invoices/{id}/pdf` and `DELETE /api/invoices/{id}` routes are reused for viewing/deleting.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db.base import get_db
from app.schemas import (
    OtherDashboardResponse,
    OtherInvoiceDetail,
    OtherInvoiceSummary,
    OtherLineItemOut,
    UploadResult,
    UploadResultItem,
)
from app.services.ingestion import ingest_other_pdf
from app.services.storage import LocalStorage

router = APIRouter(prefix="/api/other", tags=["other-invoices"])


def _raw(inv: models.Invoice) -> dict:
    raw = inv.raw_extraction or {}
    return raw if isinstance(raw, dict) else {}


def _supplier_number(inv: models.Invoice) -> str | None:
    return _raw(inv).get("supplier_number")


def _missing_fields(inv: models.Invoice) -> list[str]:
    return [r.get("field") for r in (inv.mismatch_reasons or []) if isinstance(r, dict) and r.get("field")]


def _summary(inv: models.Invoice) -> OtherInvoiceSummary:
    return OtherInvoiceSummary(
        id=inv.id,
        vendor_name=inv.vendor_name,
        invoice_number=inv.invoice_number,
        date_received=inv.date_received,
        total_invoice_cost=inv.total_invoice_cost,
        status=inv.status,
        supplier_number=_supplier_number(inv),
        budget_id=_raw(inv).get("budget_id"),
        cost_center=_raw(inv).get("cost_center"),
        offset_gl_account=_raw(inv).get("offset_gl_account"),
        approver=_raw(inv).get("approver"),
        archived_at=inv.archived_at,
        line_item_count=len(inv.line_items),
        missing_count=len(_missing_fields(inv)),
    )


@router.post("/invoices/upload", response_model=UploadResult)
async def upload_other_invoices(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
) -> UploadResult:
    """Upload hardware/software/subscription invoice PDFs and parse each with the OTHER rules only."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    storage = LocalStorage(settings.STORAGE_DIR)
    results: list[UploadResultItem] = []
    for upload in files:
        name = upload.filename or "invoice.pdf"
        if not name.lower().endswith(".pdf"):
            results.append(UploadResultItem(filename=name, ok=False, error="Not a PDF"))
            continue
        tmp_dir = Path(tempfile.mkdtemp(prefix="invoicee_other_"))
        tmp_path = tmp_dir / Path(name).name
        try:
            with tmp_path.open("wb") as out:
                shutil.copyfileobj(upload.file, out)
            inv = ingest_other_pdf(db, str(tmp_path), storage=storage)
            db.refresh(inv)
            results.append(UploadResultItem(
                filename=name, ok=True, invoice_id=inv.id,
                invoice_number=inv.invoice_number, status=inv.status,
            ))
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


@router.get("/dashboard", response_model=OtherDashboardResponse)
def other_dashboard(db: Session = Depends(get_db)) -> OtherDashboardResponse:
    """Three-column board for other invoices: Missing Data | All Data Found | All (active only)."""
    invoices = db.scalars(
        select(models.Invoice)
        .where(
            models.Invoice.invoice_type == models.INVOICE_TYPE_OTHER,
            models.Invoice.archived_at.is_(None),
        )
        .order_by(models.Invoice.created_at.desc())
    ).all()
    summaries = [_summary(i) for i in invoices]
    return OtherDashboardResponse(
        all=summaries,
        found=[s for s in summaries if s.status == models.STATUS_ALL_DATA_FOUND],
        missing=[s for s in summaries if s.status == models.STATUS_MISSING_DATA],
    )


@router.get("/history", response_model=list[OtherInvoiceSummary])
def other_history(db: Session = Depends(get_db)) -> list[OtherInvoiceSummary]:
    """Every other-type invoice in the DB (separate from the contractor History), newest first."""
    invoices = db.scalars(
        select(models.Invoice)
        .where(models.Invoice.invoice_type == models.INVOICE_TYPE_OTHER)
        .order_by(models.Invoice.created_at.desc())
    ).all()
    return [_summary(i) for i in invoices]


@router.get("/invoices/{invoice_id}", response_model=OtherInvoiceDetail)
def other_invoice_detail(invoice_id: int, db: Session = Depends(get_db)) -> OtherInvoiceDetail:
    """All parsed fields + the service line-item table + the list of any missing required fields."""
    inv = db.get(models.Invoice, invoice_id)
    if inv is None or inv.invoice_type != models.INVOICE_TYPE_OTHER:
        raise HTTPException(status_code=404, detail="Invoice not found")
    lines = [
        OtherLineItemOut(
            id=li.id,
            description=li.contractor_name,  # reused column = service description
            quantity=li.hours,               # reused column = quantity
            unit_price=li.rate,              # reused column = unit price
            amount=li.amount,
        )
        for li in inv.line_items
    ]
    return OtherInvoiceDetail(
        **_summary(inv).model_dump(),
        pdf_storage_key=inv.pdf_storage_key,
        parse_confidence=inv.parse_confidence,
        missing_fields=_missing_fields(inv),
        line_items=lines,
    )
