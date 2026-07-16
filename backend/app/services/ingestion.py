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


def _invoice_no_from_filename(stem: str) -> str:
    """Best-effort invoice number from a PDF filename when none is printed in the document.

    Prefers an embedded alphanumeric invoice code, e.g.
    'ACI0501202621760_Invoice - Acima Mobile App April 2026' -> 'ACI0501202621760'. Falls back to the
    first token containing a digit, then the whole stem.
    """
    import re

    m = re.search(r"[A-Za-z]{2,6}\d{5,}[A-Za-z0-9-]*", stem)  # letter-prefixed code like ACI0501…
    if m:
        return m.group(0)
    for tok in re.split(r"[_\s]+", stem):
        if any(c.isdigit() for c in tok):
            return tok
    return stem


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
    outcome = parse_invoice(pdf_path, db=db)  # db enables the learned-template layer
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
    inv.invoice_number = p.invoice_number or _invoice_no_from_filename(Path(pdf_path).stem)
    # Re-uploading a previously-exported (archived) invoice brings it back onto the board so it can be
    # re-tested. It's the same DB row (idempotent on invoice number), so History won't duplicate it.
    inv.archived_at = None
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
        # Advisory hints the LLM read off the invoice (CAPEX/OPEX, company code, cost center).
        # Clarity/Coupa mappings remain authoritative.
        "llm_accounting": outcome.llm_accounting,
        "template_id": outcome.template_id,
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

    # One-and-done learning: store the LLM-emitted, source-validated template so the next invoice
    # from this vendor parses without the LLM.
    if outcome.learned_template and p.vendor_name:
        from app.services.parsing import llm, templates

        db.flush()  # ensure inv.id for source_invoice_id
        tpl = templates.save_template(
            db, p.vendor_name, outcome.learned_template,
            source_invoice_id=inv.id, llm_model=llm.LLM_MODEL,
        )
        db.add(models.AuditLog(
            invoice_id=inv.id,
            event="template_learned",
            detail={"vendor_key": tpl.vendor_key, "validated": True},
        ))
    elif outcome.template_id is not None:
        db.add(models.AuditLog(
            invoice_id=inv.id,
            event="template_applied",
            detail={"template_id": outcome.template_id},
        ))

    db.commit()
    return inv


def ingest_other_pdf(db: Session, pdf_path: str, storage: LocalStorage | None = None) -> models.Invoice:
    """Ingest a hardware/software/subscription ("other") invoice. Parallel to `ingest_pdf` but uses the
    dedicated `parse_other_invoice` rules, resolves the supplier number, and routes to
    `all_data_found` vs `missing_data` — NO Clarity matching. Contractor logic is untouched.

    Line items reuse the shared columns as storage: `contractor_name`=service description,
    `hours`=quantity, `rate`=unit price, `amount`=amount.
    """
    from app.services.budget_index import budget_route
    from app.services.coupa import approver_for, supplier_number_for, tracking_accounting_for
    from app.services.parsing.other_rules import parse_other_invoice, required_missing_fields

    storage = storage or LocalStorage(settings.STORAGE_DIR)
    result = parse_other_invoice(pdf_path)
    p = result.parsed

    storage_key = storage.put_file(pdf_path)
    # Accounting routing for "other" invoices:
    #  - Copy Tracker (by invoice number): cost center + offset GL + approver, if this invoice was filed.
    #  - Budget sheet (vendor + service description): Budget ID, plus a fallback for anything the tracker
    #    lacked (cost center / offset GL / approver / supplier number).
    tracker = tracking_accounting_for(p.invoice_number)
    budget = budget_route(p.vendor_name, [li.description or "" for li in p.line_items])
    supplier_number = supplier_number_for(p.vendor_name) or budget["supplier_number"]
    accounting = {
        "budget_id": budget["budget_id"],
        "cost_center": tracker["cost_center"] or budget["cost_center"],
        "offset_gl_account": tracker["offset_gl_account"] or budget["offset_gl_account"],
        "approver": approver_for(p.vendor_name, p.invoice_number) or budget["approver"],
    }
    missing = required_missing_fields(p, supplier_number)
    status = models.STATUS_MISSING_DATA if missing else models.STATUS_ALL_DATA_FOUND

    inv = None
    if p.invoice_number:
        inv = db.scalar(
            select(models.Invoice).where(
                models.Invoice.invoice_number == p.invoice_number,
                models.Invoice.invoice_type == models.INVOICE_TYPE_OTHER,
            )
        )
    if inv is None:
        inv = db.scalar(select(models.Invoice).where(models.Invoice.pdf_storage_key == storage_key))
    if inv is None:
        inv = models.Invoice()
        db.add(inv)

    inv.invoice_type = models.INVOICE_TYPE_OTHER
    inv.vendor_name = p.vendor_name
    inv.invoice_number = p.invoice_number or _invoice_no_from_filename(Path(pdf_path).stem)
    inv.archived_at = None
    inv.date_received = p.date_received
    inv.payment_period_start = inv.payment_period_end = None
    inv.total_invoice_cost = p.total_invoice_cost
    inv.status = status
    inv.mismatch_reasons = [
        {"field": f, "reason": "Required field could not be parsed.",
         "invoice_value": None, "clarity_value": None}
        for f in missing
    ]
    inv.pdf_storage_key = storage_key
    inv.parse_confidence = None
    inv.raw_extraction = {
        "method": result.method,
        "supplier_number": supplier_number,
        "budget_id": accounting["budget_id"],
        "cost_center": accounting["cost_center"],
        "offset_gl_account": accounting["offset_gl_account"],
        "approver": accounting["approver"],
        "missing_fields": missing,
        "parsed": p.model_dump(mode="json"),
        "warnings": result.warnings,
    }

    inv.line_items.clear()
    db.flush()
    for li in p.line_items:
        inv.line_items.append(
            models.InvoiceLineItem(
                contractor_name=li.description,   # reused column = service description
                hours=li.quantity,                # reused column = quantity
                rate=li.unit_price,               # reused column = unit price
                amount=li.amount,
                line_status=None,
            )
        )

    db.add(models.AuditLog(
        invoice_id=inv.id,
        event="parsed_other",
        detail={"method": result.method, "supplier_number": supplier_number,
                "line_items": len(p.line_items), "status": status, "missing": missing},
    ))
    db.commit()
    return inv
