"""Executive report API: aggregate all processed invoices + optional LLM narrative.

The LLM is invoked ONLY when these endpoints are hit (i.e. someone clicked "Create Report") —
never in the background.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db.base import get_db
from app.services import reporting

router = APIRouter(prefix="/api", tags=["reports"])


class ReportRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class ReportResponse(BaseModel):
    aggregates: dict
    narrative: str | None = None
    llm_available: bool = False
    generated_at: datetime


def _build(db: Session, body: ReportRequest) -> ReportResponse:
    aggregates = reporting.compute_aggregates(db, body.start_date, body.end_date)
    narrative = reporting.generate_narrative(aggregates)
    db.add(models.AuditLog(
        invoice_id=None,
        event="report_generated",
        detail={
            "start": body.start_date.isoformat() if body.start_date else None,
            "end": body.end_date.isoformat() if body.end_date else None,
            "invoices": aggregates["period"]["generated_from_invoices"],
            "llm": narrative is not None,
        },
    ))
    db.commit()
    return ReportResponse(
        aggregates=aggregates,
        narrative=narrative,
        llm_available=bool(settings.ANTHROPIC_API_KEY),
        generated_at=datetime.now(),
    )


@router.post("/reports", response_model=ReportResponse)
def create_report(body: ReportRequest, db: Session = Depends(get_db)) -> ReportResponse:
    """Aggregates + AI narrative for the in-app report modal."""
    return _build(db, body)


@router.post("/reports/html")
def create_report_html(body: ReportRequest, db: Session = Depends(get_db)) -> Response:
    """Self-contained standalone HTML report (inline CSS + SVG charts, no external requests)."""
    from app.services.report_html import report_html_bytes

    result = _build(db, body)
    html = report_html_bytes(result.aggregates, result.narrative)
    stamp = datetime.now().strftime("%Y-%m-%d")
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="invoice-report-{stamp}.html"'},
    )
