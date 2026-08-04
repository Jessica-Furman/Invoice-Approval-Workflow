"""Populate `clarity_resources` with each contractor's cost center (department DT code).

The DT cost center lives only in the Clarity Resources API — the resource record's `department`
lookup (its `id` is the DT code, e.g. 'DT500') — NOT in the TimeEntry export we import for hours.
So we sync it separately: take the distinct contractors we actually have Clarity timesheets for,
look each up in the Resources API, and upsert their DT code keyed by normalized name.

Used by CSV/Excel/drawer generation for OPEX cost-center coding (CapEx work uses the company cost
center H0003/AC000 instead — see coupa.py). Read side is `cost_center_map`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.services import clarity_api
from app.utils.names import normalize_name


@dataclass
class ResourceSyncResult:
    contractors: int = 0
    resolved: int = 0
    created: int = 0
    updated: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "contractors": self.contractors,
            "resolved": self.resolved,
            "created": self.created,
            "updated": self.updated,
            "warnings": self.warnings,
        }


def _distinct_contractors(db: Session) -> dict[str, str]:
    """{normalized_name -> display_name} for every contractor we have Clarity timesheets for."""
    rows = db.execute(
        select(
            models.ClarityTimesheet.contractor_name_normalized,
            models.ClarityTimesheet.contractor_name,
        ).distinct()
    ).all()
    out: dict[str, str] = {}
    for norm, disp in rows:
        if norm and norm not in out:
            out[norm] = disp or norm
    return out


def _sync(db: Session, by_display: dict[str, str]) -> ResourceSyncResult:
    """Fetch each display name's department DT code from the Resources API and upsert into
    `clarity_resources` (idempotent on normalized name). `by_display` is {display name -> normalized}."""
    result = ResourceSyncResult()
    result.contractors = len(by_display)
    if not by_display:
        return result

    fetched = clarity_api.fetch_resource_cost_centers(list(by_display.keys()))
    result.resolved = len(fetched)

    existing = {
        r.contractor_name_normalized: r
        for r in db.scalars(select(models.ClarityResource)).all()
        if r.contractor_name_normalized
    }

    for display, info in fetched.items():
        norm = by_display.get(display)
        if not norm:
            continue
        fields = dict(
            contractor_name=display,
            contractor_name_normalized=norm,
            cost_center=info.get("cost_center"),
            department_name=info.get("department_name"),
            resource_id=info.get("resource_id"),
        )
        row = existing.get(norm)
        if row is None:
            row = models.ClarityResource(**fields)
            db.add(row)
            existing[norm] = row
            result.created += 1
        else:
            for k, v in fields.items():
                setattr(row, k, v)
            result.updated += 1
    db.commit()
    return result


def sync_resource_cost_centers(db: Session) -> ResourceSyncResult:
    """Fetch every distinct Clarity contractor's department DT code from the Resources API (full sync;
    the API resolves on the display 'First Last' form)."""
    return _sync(db, {disp: norm for norm, disp in _distinct_contractors(db).items()})


def sync_resource_cost_centers_for(db: Session, contractor_names: list[str]) -> ResourceSyncResult:
    """Targeted sync for a specific set of invoice contractor names (used per invoice-upload so a new
    contractor's DT cost center is fetched without a full re-sync)."""
    by_display: dict[str, str] = {}
    for nm in contractor_names:
        if nm and nm not in by_display:
            by_display[nm] = normalize_name(nm)
    return _sync(db, by_display)


def cost_center_map(db: Session) -> dict[str, str]:
    """{normalized_name -> DT cost center} for contractors we've synced a department code for."""
    return {
        r.contractor_name_normalized: r.cost_center
        for r in db.scalars(select(models.ClarityResource)).all()
        if r.contractor_name_normalized and r.cost_center
    }


def _main() -> None:
    from app.db.base import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        res = sync_resource_cost_centers(db)
        print("Clarity resource cost-center sync complete:")
        for k, v in res.as_dict().items():
            print(f"  {k}: {v}")
    finally:
        db.close()


if __name__ == "__main__":
    _main()
