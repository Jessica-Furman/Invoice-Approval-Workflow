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

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.utils.names import normalize_name

FUZZY_STRONG = 80             # accept a fuzzy name match outright at/above this similarity (0-100)
FUZZY_ANCHORED_MIN = 65       # accept down to this similarity IF the names share a real component
HOURS_ABS_TOLERANCE = 1.0     # hours
HOURS_PCT_TOLERANCE = 0.02    # 2%


def _name_similarity(a: str, b: str) -> float:
    """Best-of several fuzzy signals — robust to token order, a missing surname, concatenated
    names ('SaravanaPerumal' vs 'Saravana Perumal') and split names ('Sri Soorya' vs 'Srisoorya').

    token_set_ratio rewards an exactly-shared name component; the despaced ratios (computed only
    when both names are long enough that a short fragment can't match everything) handle spacing.
    """
    a2, b2 = a.replace(" ", ""), b.replace(" ", "")
    scores = [fuzz.token_sort_ratio(a, b), fuzz.token_set_ratio(a, b)]
    if min(len(a2), len(b2)) >= 7:
        scores.append(fuzz.ratio(a2, b2))
        scores.append(fuzz.partial_ratio(a2, b2))
    return max(scores)


def _shares_anchor(a: str, b: str) -> bool:
    """True if two names share a real component: a common token (>=3 chars) or one despaced name
    contained in the other. Gates the lenient 70% threshold so coincidental near-misses (e.g.
    'Michael Johnson' vs 'Jon Nelson') aren't accepted."""
    ta = {t for t in a.split() if len(t) >= 3}
    tb = {t for t in b.split() if len(t) >= 3}
    if ta & tb:
        return True
    a2, b2 = a.replace(" ", ""), b.replace(" ", "")
    short, long = sorted((a2, b2), key=len)
    return len(short) >= 6 and short in long


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
        # Fuzzy: multi-signal similarity that tolerates token order, a missing surname, and
        # concatenated/split names. Accept the best candidate if it's a strong match, or a 70%+
        # match that shares a real name component (so partial invoice names still resolve).
        if self.distinct_norms:
            best_name, best_score = None, 0.0
            for cand in self.distinct_norms:
                sc = _name_similarity(norm, cand)
                if sc > best_score:
                    best_score, best_name = sc, cand
            if best_name and (
                best_score >= FUZZY_STRONG
                or (best_score >= FUZZY_ANCHORED_MIN and _shares_anchor(norm, best_name))
            ):
                return best_name, "fuzzy"
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


@dataclass
class ClarityHours:
    """Result of summing a contractor's Clarity hours for an invoice period."""

    posted: float                              # billable POSTED hours (what we match against)
    rows: list[models.ClarityTimesheet]        # the posted rows used
    period_constrained: bool                   # False if no invoice period was available
    pending: float = 0.0                       # billable hours SUBMITTED but not yet posted (same window)


def _clarity_hours_for(
    rows: list[models.ClarityTimesheet], inv_start: date | None, inv_end: date | None
) -> ClarityHours:
    """Sum billable Clarity hours for the contractor:
    - only POSTED timesheets (Time Sheet Status == "Posted"),
    - EXCLUDING time-off entries (Time Off / PTO / timeoff), and
    - restricted to entries whose Date Worked falls within the invoice period (when known).

    Also sums billable but NOT-yet-posted hours (e.g. Time Sheet Status "Submitted") in the same
    window so the caller can distinguish "real discrepancy" from "Clarity hasn't posted yet".
    """
    def _in_window(r: models.ClarityTimesheet) -> bool:
        if inv_start and inv_end:
            return bool(r.date_worked and inv_start <= r.date_worked <= inv_end)
        return True

    posted_rows = [r for r in rows if r.is_posted and not r.is_time_off and _in_window(r)]
    pending = sum(r.hours or 0 for r in rows if not r.is_posted and not r.is_time_off and _in_window(r))
    return ClarityHours(
        posted=sum(r.hours or 0 for r in posted_rows),
        rows=posted_rows,
        period_constrained=bool(inv_start and inv_end),
        pending=round(pending, 2),
    )


def _hours_reason(
    name: str | None, inv_hours: float, clarity_hours: float, pending: float,
    pending_posting: bool, prefix: str = "",
) -> dict:
    """Build a mismatch reason for an hours discrepancy.

    When the shortfall is explained by time that's submitted-but-not-yet-posted in Clarity, say so
    explicitly — it's a timing issue (await Clarity posting), not a true hours discrepancy.
    """
    inv_r, cl_r = round(inv_hours, 2), round(clarity_hours, 2)
    if pending_posting:
        reason = (
            f"{prefix}{name}: invoice bills {inv_r} hrs but only {cl_r} are posted in Clarity for "
            f"this period; {round(pending, 2)} more hrs are submitted/awaiting posting. "
            f"Reconcile once Clarity posts."
        )
    else:
        reason = f"{prefix}Hours differ for {name} (invoice {inv_r} vs Clarity {cl_r})."
    return {
        "field": "hours", "reason": reason,
        "invoice_value": str(inv_r), "clarity_value": str(cl_r),
    }


def match_invoice(db: Session, invoice: models.Invoice, index: ClarityIndex) -> None:
    if invoice.status == models.STATUS_FAILED:
        return  # can't match what we couldn't parse

    reasons: list[dict] = []
    line_statuses: list[str] = []

    items = list(invoice.line_items)
    resolutions = [(li, *index.resolve(li.contractor_name)) for li in items]
    resolved_norms = {norm for (_, norm, _) in resolutions if norm}

    # Special case: a single contractor billed across multiple lines (e.g. weekly splits, like Amandh).
    # Only when EVERY line resolves to the SAME one contractor do we compare the summed invoice hours
    # to that contractor's Clarity total. All other invoices keep per-line matching.
    single_contractor = (
        len(items) > 1
        and len(resolved_norms) == 1
        and all(norm for (_, norm, _) in resolutions)
    )

    if single_contractor:
        norm = next(iter(resolved_norms))
        method = resolutions[0][2]
        rows = index.by_norm[norm]
        # Use the invoice-level period (per-line week dates on these split invoices can be unreliable).
        ch = _clarity_hours_for(rows, invoice.payment_period_start, invoice.payment_period_end)
        clarity_hours, used_rows = ch.posted, ch.rows
        # Link to a posted row if any, else any row of the resolved contractor — so the UI drill-down
        # can still show this person's entries (e.g. submitted-but-not-posted) when 0 posted hours.
        link_row = used_rows[0] if used_rows else (rows[0] if rows else None)
        clarity_name = link_row.contractor_name if link_row else None
        inv_total = sum((li.hours or 0) for li in items)
        delta = inv_total - clarity_hours
        ok = abs(delta) <= max(HOURS_ABS_TOLERANCE, HOURS_PCT_TOLERANCE * inv_total)
        pending_posting = (not ok) and delta > 0 and ch.pending > 0
        status = models.STATUS_MATCHED if ok else models.STATUS_FLAGGED
        for li, _, _ in resolutions:
            li.matched_clarity_id = link_row.id if link_row else None
            li.line_status = status
            li.diff = {
                "match_method": method, "clarity_name": clarity_name, "aggregated": True,
                "invoice_hours": li.hours, "contractor_invoice_total": round(inv_total, 2),
                "clarity_hours": round(clarity_hours, 2), "clarity_pending_hours": ch.pending,
                "pending_posting": pending_posting, "hours_delta": round(delta, 2),
                "rate_validated": False,
            }
            line_statuses.append(status)
        if not ok:
            reasons.append(_hours_reason(
                clarity_name or items[0].contractor_name, inv_total, clarity_hours, ch.pending,
                pending_posting, prefix=f"Total across {len(items)} lines: ",
            ))
        invoice.status = models.STATUS_MATCHED if status == models.STATUS_MATCHED else models.STATUS_FLAGGED
        invoice.mismatch_reasons = reasons
        db.add(models.AuditLog(
            invoice_id=invoice.id, event="matched",
            detail={"status": invoice.status, "mode": "single_contractor_total",
                    "lines": len(items), "matched_lines": len(items) if status == models.STATUS_MATCHED else 0},
        ))
        return

    for li, clarity_norm, method in resolutions:
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
        ch = _clarity_hours_for(rows, line_start, line_end)
        clarity_hours, used_rows = ch.posted, ch.rows
        # Link to a posted row if any, else any row of the resolved contractor — so the UI drill-down
        # still shows this person's entries (e.g. submitted-but-not-posted) when 0 posted hours.
        link_row = used_rows[0] if used_rows else (rows[0] if rows else None)
        li.matched_clarity_id = link_row.id if link_row else None
        inv_hours = li.hours

        diff = {
            "match_method": method,
            "clarity_name": link_row.contractor_name if link_row else None,
            "invoice_hours": inv_hours,
            "clarity_hours": round(clarity_hours, 2),
            "clarity_pending_hours": ch.pending,
            "period_constrained": ch.period_constrained,
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
                # Distinguish a real discrepancy from time that's simply not posted in Clarity yet.
                pending_posting = delta > 0 and ch.pending > 0
                diff["pending_posting"] = pending_posting
                reasons.append(_hours_reason(
                    li.contractor_name, inv_hours, clarity_hours, ch.pending, pending_posting,
                ))
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
