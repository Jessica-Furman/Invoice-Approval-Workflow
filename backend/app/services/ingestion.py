"""Ingest a contractor invoice PDF: store the file, parse it, and upsert the invoice record.

For the MVP this is driven by a CLI over the 5 sample PDFs. Later (M8) the same `ingest_pdf` will be
called by the Outlook inbox watcher when new invoices arrive.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services.parsing import parse_invoice
from app.services.parsing.rules import parse_date
from app.services.storage import LocalStorage
from app.utils.names import normalize_name


def parse_period(period: str | None) -> tuple[date | None, date | None]:
    """Split a 'start - end' / 'start to end' period string into two dates (best effort).

    The separator must be a dash/'to' surrounded by whitespace (or an en-dash), so a date that
    itself contains hyphens (e.g. '02-Mar-2026 - 31-Mar-2026') isn't split at its internal hyphen.
    """
    if not period:
        return None, None
    import re

    parts = re.split(r"\s+-\s+|\s*–\s*|\s+to\s+", period, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        return parse_date(parts[0]), parse_date(parts[1])
    return parse_date(period), None


def _status_and_reasons(outcome) -> tuple[str, list[dict]]:
    if not outcome.has_text and not outcome.parsed.line_items:
        return models.STATUS_FAILED, [
            {"field": "document", "reason": "PDF has no extractable text (scanned) — needs OCR/vision.",
             "invoice_value": None, "clarity_value": None}
        ]
    missing = outcome.missing_required()
    if missing:
        return models.STATUS_NEEDS_REVIEW, [
            {"field": f, "reason": "Required field could not be parsed.",
             "invoice_value": None, "clarity_value": None}
            for f in missing
        ]
    # Parsed cleanly but not yet matched against Clarity — pending review until M4 matching runs.
    return models.STATUS_NEEDS_REVIEW, []


def ingest_pdf(db: Session, pdf_path: str, storage: LocalStorage | None = None) -> models.Invoice:
    storage = storage or LocalStorage(settings.STORAGE_DIR)
    outcome = parse_invoice(pdf_path)
    p = outcome.parsed

    storage_key = storage.put_file(pdf_path)
    status, reasons = _status_and_reasons(outcome)

    # Idempotent on invoice_number when present; otherwise on the stored filename.
    inv = None
    if p.invoice_number:
        inv = db.scalar(select(models.Invoice).where(models.Invoice.invoice_number == p.invoice_number))
    if inv is None:
        inv = db.scalar(select(models.Invoice).where(models.Invoice.pdf_storage_key == storage_key))
    if inv is None:
        inv = models.Invoice()
        db.add(inv)

    inv.vendor_name = p.vendor_name
    inv.invoice_number = p.invoice_number or Path(pdf_path).stem
    inv.date_received = p.date_received
    # Period priority: a labeled "Period:" header is authoritative (handles invoices whose per-line
    # dates have typos); otherwise use the full span of the line-item periods (handles invoices like
    # the scanned Healy one where the header has no period); otherwise an unlabeled header range.
    line_starts = [date.fromisoformat(li.extra["period_start"]) for li in p.line_items
                   if li.extra and li.extra.get("period_start")]
    line_ends = [date.fromisoformat(li.extra["period_end"]) for li in p.line_items
                 if li.extra and li.extra.get("period_end")]
    if p.payment_period_labeled:
        period_start, period_end = parse_period(p.payment_period)
    elif line_starts and line_ends:
        period_start, period_end = min(line_starts), max(line_ends)
    else:
        period_start, period_end = parse_period(p.payment_period)
    inv.payment_period_start, inv.payment_period_end = period_start, period_end
    inv.total_invoice_cost = p.total_invoice_cost
    inv.status = status
    inv.mismatch_reasons = reasons
    inv.pdf_storage_key = storage_key
    inv.parse_confidence = outcome.confidence
    inv.raw_extraction = {
        "method": outcome.method,
        "payment_period": p.payment_period,
        "parsed": p.model_dump(mode="json"),
        "warnings": outcome.warnings,
    }

    # Replace line items.
    inv.line_items.clear()
    db.flush()
    for li in p.line_items:
        inv.line_items.append(
            models.InvoiceLineItem(
                contractor_name=li.contractor_name,
                contractor_name_normalized=normalize_name(li.contractor_name),
                hours=li.hours,
                rate=li.rate,
                amount=li.amount,
                line_status=None,  # set during matching (M4)
                extra=li.extra or {},
            )
        )

    db.add(models.AuditLog(
        invoice_id=inv.id,
        event="parsed",
        detail={"method": outcome.method, "confidence": outcome.confidence,
                "line_items": len(p.line_items), "status": status},
    ))
    db.commit()
    return inv
