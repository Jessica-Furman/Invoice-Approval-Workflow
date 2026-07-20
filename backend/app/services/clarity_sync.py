"""Orchestrates a live Clarity sync ahead of matching, with CSV as the fallback of record.

Called once per invoice-upload batch (see `api/invoices.py`) before `ClarityIndex.build`, so
matching always reads whatever is freshest in `clarity_timesheets`. A failed/unconfigured API never
raises past this module — the invoice pipeline must keep working on cached or manually-imported
CSV data, just with `ClaritySyncStatus` recording why.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app import models
from app.services import clarity_api
from app.services.clarity_import import import_dataframe

logger = logging.getLogger(__name__)


def _get_status(db: Session) -> models.ClaritySyncStatus:
    status = db.get(models.ClaritySyncStatus, 1)
    if status is None:
        status = models.ClaritySyncStatus(id=1)
        db.add(status)
    return status


def sync_contractors(
    db: Session, contractor_names: list[str], start: date | None, end: date | None
) -> None:
    """Try to refresh Clarity data for these contractors via the live API; fall back silently."""
    status = _get_status(db)
    status.last_attempt_at = datetime.utcnow()

    if not contractor_names or not clarity_api.is_configured():
        status.source = "unconfigured"
        db.commit()
        return

    try:
        df = clarity_api.fetch_timesheets(contractor_names, start, end)
        import_dataframe(db, df)
        status.source = "api"
        status.last_success_at = datetime.utcnow()
        status.last_error = None
    except Exception as e:  # noqa: BLE001 - any failure here must fall back, never block uploads
        logger.warning("Clarity API sync failed, falling back to cached/CSV data: %s", e)
        status.source = "csv_fallback"
        status.last_error = str(e)

    db.commit()
