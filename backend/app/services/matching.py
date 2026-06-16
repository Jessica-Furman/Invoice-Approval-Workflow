"""Invoice-to-Clarity matching (M4) — partial match on contractor name + hours.

Clarity has no pay rate, so rate is not validated here (recorded as not-validated). For each invoice
line we:
  1. Resolve the contractor to a Clarity name: exact normalized -> cross-reference table -> fuzzy.
  2. Sum that contractor's Clarity hours over the invoice's payment period (or all hours if the
     invoice period can't be parsed).
  3. Compare invoiced hours vs Clarity hours within a tolerance -> matched / flagged.

Invoice status is derived from its line items (User Story 11). Results, diffs, and mismatch reasons
are persisted so the UI can show exactly what did/didn't line up.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.utils.names import normalize_name

FUZZY_THRESHOLD = 80          # rapidfuzz token_sort_ratio (0-100) to accept a fuzzy name match
HOURS_ABS_TOLERANCE = 1.0     # hours
HOURS_PCT_TOLERANCE = 0.02    # 2%


def _sorted_key(norm: str) -> str:
    """Order-insensitive key: 'gurijala chaitra' and 'chaitra gurijala' -> 'chaitra gurijala'.

    Invoices use 'First Last' while Clarity is 'Last, First', so token order can differ even for
    the same person; sorting the tokens makes the exact match order-independent.
    """
    return " ".join(sorted(norm.split()))


@dataclass
class ClarityIndex:
    by_norm: dict[str, list[models.ClarityTimesheet]]
    distinct_norms: list[str]
    by_sorted: dict[str, str]  # sorted-token key -> a representative normalized Clarity name
    crossref: dict[str, str]   # normalized invoice name -> Clarity display name

    @classmethod
    def build(cls, db: Session) -> "ClarityIndex":
        by_norm: dict[str, list[models.ClarityTimesheet]] = defaultdict(list)
        for ts in db.scalars(select(models.ClarityTimesheet)).all():
            if ts.contractor_name_normalized:
                by_norm[ts.contractor_name_normalized].append(ts)
        by_sorted = {_sorted_key(n): n for n in by_norm}
        crossref = {
            normalize_name(c.invoice_name): c.clarity_name
            for c in db.scalars(select(models.NameCrossref)).all()
            if c.invoice_name
        }
        return cls(by_norm, list(by_norm.keys()), by_sorted, crossref)

    def resolve(self, name: str | None) -> tuple[str | None, str]:
        """Return (clarity_normalized_name, method)."""
        norm = normalize_name(name)
        if not norm:
            return None, "unresolved"
        if norm in self.by_norm:
            return norm, "exact"
        # Order-insensitive exact match (handles First/Last vs Last/First token order).
        skey = _sorted_key(norm)
        if skey in self.by_sorted:
            return self.by_sorted[skey], "exact"
        if norm in self.crossref:
            target = normalize_name(self.crossref[norm])
            if target in self.by_norm:
                return target, "crossref"
        # Fuzzy: token_sort_ratio is order-insensitive and tolerant of minor spelling differences.
        if self.distinct_norms:
            hit = process.extractOne(norm, self.distinct_norms, scorer=fuzz.token_sort_ratio)
            if hit and hit[1] >= FUZZY_THRESHOLD:
                return hit[0], "fuzzy"
        return None, "unresolved"


def _iso_to_date(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _line_period(li: models.InvoiceLineItem, invoice: models.Invoice) -> tuple[date | None, date | None]:
    """Period to filter Clarity by: the line item's own period if parsed, else the invoice period."""
    extra = li.extra or {}
    ls = _iso_to_date(extra.get("period_start"))
    le = _iso_to_date(extra.get("period_end"))
    if ls and le:
        return ls, le
    return invoice.payment_period_start, invoice.payment_period_end


def _clarity_hours_for(
    rows: list[models.ClarityTimesheet], inv_start: date | None, inv_end: date | None
) -> tuple[float, list[models.ClarityTimesheet], bool]:
    """Sum billable Clarity hours for the contractor:
    - only POSTED timesheets,
    - EXCLUDING time-off entries (Time Off / PTO / timeoff), and
    - restricted to entries whose Date Worked falls within the invoice period (when known).
    """
    billable = [r for r in rows if r.is_posted and not r.is_time_off]
    if inv_start and inv_end:
        in_period = [r for r in billable if r.date_worked and inv_start <= r.date_worked <= inv_end]
        return sum(r.hours or 0 for r in in_period), in_period, True
    # No invoice period available: fall back to all billable hours (and flag that it wasn't constrained).
    return sum(r.hours or 0 for r in billable), billable, False


def match_invoice(db: Session, invoice: models.Invoice, index: ClarityIndex) -> None:
    if invoice.status == models.STATUS_FAILED:
        return  # can't match what we couldn't parse

    reasons: list[dict] = []
    line_statuses: list[str] = []

    for li in invoice.line_items:
        clarity_norm, method = index.resolve(li.contractor_name)

        if clarity_norm is None:
            li.line_status = models.STATUS_FLAGGED
            li.matched_clarity_id = None
            li.diff = {"match_method": "unresolved", "reason": "No Clarity contractor match"}
            line_statuses.append(models.STATUS_FLAGGED)
            reasons.append({
                "field": "name", "reason": f"No Clarity match for '{li.contractor_name}'.",
                "invoice_value": li.contractor_name, "clarity_value": None,
            })
            continue

        rows = index.by_norm[clarity_norm]
        # Prefer the line item's own period (TCS puts it per line); fall back to the invoice period.
        line_start, line_end = _line_period(li, invoice)
        clarity_hours, used_rows, period_constrained = _clarity_hours_for(rows, line_start, line_end)
        li.matched_clarity_id = used_rows[0].id if used_rows else None
        inv_hours = li.hours

        diff = {
            "match_method": method,
            "clarity_name": used_rows[0].contractor_name if used_rows else None,
            "invoice_hours": inv_hours,
            "clarity_hours": round(clarity_hours, 2),
            "period_constrained": period_constrained,
            "rate_validated": False,  # Clarity has no rate
        }

        if inv_hours is None:
            li.line_status = models.STATUS_FLAGGED
            diff["reason"] = "Invoice hours missing"
            reasons.append({
                "field": "hours", "reason": f"Invoice hours missing for {li.contractor_name}.",
                "invoice_value": None, "clarity_value": str(clarity_hours),
            })
        else:
            tolerance = max(HOURS_ABS_TOLERANCE, HOURS_PCT_TOLERANCE * inv_hours)
            delta = inv_hours - clarity_hours
            diff["hours_delta"] = round(delta, 2)
            if abs(delta) <= tolerance:
                li.line_status = models.STATUS_MATCHED
            else:
                li.line_status = models.STATUS_FLAGGED
                reasons.append({
                    "field": "hours",
                    "reason": f"Hours differ for {li.contractor_name} "
                              f"(invoice {inv_hours} vs Clarity {round(clarity_hours, 2)}).",
                    "invoice_value": str(inv_hours), "clarity_value": str(round(clarity_hours, 2)),
                })
        li.diff = diff
        line_statuses.append(li.line_status)

    # Derive invoice status from its lines.
    if line_statuses and all(s == models.STATUS_MATCHED for s in line_statuses):
        invoice.status = models.STATUS_MATCHED
    else:
        invoice.status = models.STATUS_FLAGGED
    invoice.mismatch_reasons = reasons

    db.add(models.AuditLog(
        invoice_id=invoice.id,
        event="matched",
        detail={
            "status": invoice.status,
            "lines": len(line_statuses),
            "matched_lines": sum(1 for s in line_statuses if s == models.STATUS_MATCHED),
        },
    ))


def match_all(db: Session) -> dict:
    index = ClarityIndex.build(db)
    invoices = db.scalars(select(models.Invoice)).all()
    counts = {models.STATUS_MATCHED: 0, models.STATUS_FLAGGED: 0, models.STATUS_FAILED: 0}
    for inv in invoices:
        match_invoice(db, inv, index)
        counts[inv.status] = counts.get(inv.status, 0) + 1
    db.commit()
    return counts


def _main() -> None:
    from app.db.base import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        counts = match_all(db)
        print("Matching complete:", counts)
    finally:
        db.close()


if __name__ == "__main__":
    _main()
