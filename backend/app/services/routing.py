"""Route invoices to the matched/flagged inbox after matching (User Stories 12-13).

Mocks Outlook for the MVP: copies the stored PDF into data/inbox/matched/ or data/inbox/flagged/
based on the invoice status, and records the action on the invoice + audit log. Idempotent — re-routing
moves the file to the correct folder and removes any stale copy from the other folder.

Swap LocalFolderInbox for a Microsoft Graph implementation in M8 without changing callers.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services.storage import LocalStorage

ROUTE_MATCHED = "matched"
ROUTE_FLAGGED = "flagged"


def _target_label(status: str) -> str:
    return ROUTE_MATCHED if status == models.STATUS_MATCHED else ROUTE_FLAGGED


def route_invoice(db: Session, invoice: models.Invoice, storage: LocalStorage | None = None) -> str:
    storage = storage or LocalStorage(settings.STORAGE_DIR)
    label = _target_label(invoice.status)
    matched_dir = Path(settings.INBOX_MATCHED_DIR)
    flagged_dir = Path(settings.INBOX_FLAGGED_DIR)
    target_dir = matched_dir if label == ROUTE_MATCHED else flagged_dir

    key = invoice.pdf_storage_key
    if key and storage.exists(key):
        target_dir.mkdir(parents=True, exist_ok=True)
        # Remove any stale copy from the other folder (status may have changed on re-match).
        other = flagged_dir if label == ROUTE_MATCHED else matched_dir
        stale = other / key
        if stale.exists():
            stale.unlink()
        shutil.copyfile(storage.path_for(key), target_dir / key)

    invoice.routed_to = label
    db.add(models.AuditLog(
        invoice_id=invoice.id,
        event="routed",
        detail={"to": label, "status": invoice.status, "file": key},
    ))
    return label


def route_all(db: Session) -> dict:
    counts = {ROUTE_MATCHED: 0, ROUTE_FLAGGED: 0}
    for inv in db.scalars(select(models.Invoice)).all():
        counts[route_invoice(db, inv)] += 1
    db.commit()
    return counts


def _main() -> None:
    from app.db.base import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        print("Routing complete:", route_all(db))
    finally:
        db.close()


if __name__ == "__main__":
    _main()
