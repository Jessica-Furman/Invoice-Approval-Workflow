"""SQLAlchemy ORM models for the invoice processing system.

JSON columns use SQLAlchemy's generic JSON type — stored as JSON on SQLite and as JSONB-compatible
JSON on Postgres, so the same models work across both backends.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Invoice status values (User Story 11)
STATUS_MATCHED = "matched"
STATUS_FLAGGED = "flagged"
STATUS_NEEDS_REVIEW = "needs_manual_review"
STATUS_FAILED = "processing_failed"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(128), index=True)
    date_received: Mapped[date | None] = mapped_column(Date)
    payment_period_start: Mapped[date | None] = mapped_column(Date)
    payment_period_end: Mapped[date | None] = mapped_column(Date)
    total_invoice_cost: Mapped[float | None] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(32), default=STATUS_NEEDS_REVIEW, index=True)
    # List of {field, reason, invoice_value, clarity_value} dicts (User Stories 16, 26).
    mismatch_reasons: Mapped[list | None] = mapped_column(JSON, default=list)

    pdf_storage_key: Mapped[str | None] = mapped_column(String(512))
    # Full unmodified parser output (User Story 3); line-item shape may evolve.
    raw_extraction: Mapped[dict | None] = mapped_column(JSON, default=dict)
    parse_confidence: Mapped[float | None] = mapped_column(Float)

    coupa_csv_generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLineItem(Base):
    """Per-contractor line on an invoice. Thin typed columns + JSONB-style `extra` on purpose:
    the line-item shape is expected to change as real invoice formats are learned."""

    __tablename__ = "invoice_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)

    contractor_name: Mapped[str | None] = mapped_column(String(255))
    contractor_name_normalized: Mapped[str | None] = mapped_column(String(255), index=True)
    hours: Mapped[float | None] = mapped_column(Float)
    rate: Mapped[float | None] = mapped_column(Float)
    amount: Mapped[float | None] = mapped_column(Float)

    matched_clarity_id: Mapped[int | None] = mapped_column(
        ForeignKey("clarity_timesheets.id"), nullable=True
    )
    line_status: Mapped[str | None] = mapped_column(String(32))
    # {hours_delta, rate_delta, amount_delta, ...}
    diff: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # Anything we don't yet model on a typed column.
    extra: Mapped[dict | None] = mapped_column(JSON, default=dict)

    invoice: Mapped["Invoice"] = relationship(back_populates="line_items")
    matched_clarity: Mapped["ClarityTimesheet | None"] = relationship()


class ClarityTimesheet(Base):
    __tablename__ = "clarity_timesheets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contractor_name: Mapped[str | None] = mapped_column(String(255))
    contractor_name_normalized: Mapped[str | None] = mapped_column(String(255), index=True)
    hours: Mapped[float | None] = mapped_column(Float)
    rate: Mapped[float | None] = mapped_column(Float)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    project_id: Mapped[str | None] = mapped_column(String(128), index=True)
    # Idempotent upsert key (hash of the source row) so re-imports don't duplicate.
    source_row_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)


class ClarityProject(Base):
    __tablename__ = "clarity_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(String(128), index=True)
    project_name: Mapped[str | None] = mapped_column(String(255))
    budget_id: Mapped[str | None] = mapped_column(String(128))
    capex_opex: Mapped[str | None] = mapped_column(String(16))
    cost_center: Mapped[str | None] = mapped_column(String(128))
    vendor: Mapped[str | None] = mapped_column(String(255))
    lob: Mapped[str | None] = mapped_column(String(128))
    spend: Mapped[float | None] = mapped_column(Float)


class NameCrossref(Base):
    """Invoice-name -> Clarity-name mappings (User Story 7)."""

    __tablename__ = "name_crossref"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_name: Mapped[str] = mapped_column(String(255), index=True)
    clarity_name: Mapped[str] = mapped_column(String(255))


class ProjectManagerCrossref(Base):
    """Vendor/project -> first approval-chain manager (User Stories 22-23)."""

    __tablename__ = "project_manager_crossref"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor: Mapped[str | None] = mapped_column(String(255), index=True)
    project_id: Mapped[str | None] = mapped_column(String(128), index=True)
    manager_name: Mapped[str | None] = mapped_column(String(255))
    manager_email: Mapped[str | None] = mapped_column(String(255))


class AuditLog(Base):
    """Append-only processing history (User Story 25)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    event: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


__all__ = [
    "Invoice",
    "InvoiceLineItem",
    "ClarityTimesheet",
    "ClarityProject",
    "NameCrossref",
    "ProjectManagerCrossref",
    "AuditLog",
    "STATUS_MATCHED",
    "STATUS_FLAGGED",
    "STATUS_NEEDS_REVIEW",
    "STATUS_FAILED",
]
