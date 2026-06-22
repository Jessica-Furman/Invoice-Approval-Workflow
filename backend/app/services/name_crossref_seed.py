"""Confirmed invoice-name -> Clarity-name cross-references (User Story 7).

Some vendors print a contractor's full name while Clarity stores an anonymized, abbreviated, or
nickname form. These confirmed mappings let matching resolve them when exact/order-insensitive/
fuzzy resolution can't (e.g. an anonymized first name shares only the surname). Seeded by
`bootstrap` and idempotent on `invoice_name`, so a rebuild keeps them.

Add new confirmed mappings to KNOWN_CROSSREFS. Resolution then goes:
invoice name -> (this map) -> Clarity display name -> normalized -> Clarity timesheets.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models

# invoice_name -> clarity_name (both as they appear; matching normalizes them).
# Ironin invoice vs Clarity: anonymized first names ("P1"/"P2") and a Polish nickname (Tomek=Tomasz).
KNOWN_CROSSREFS: dict[str, str] = {
    "Przemek Szyszka": "P1 Szyszka",
    "Przemek Sienkowski": "P2 Sienkowski",
    "Tomasz Nazar": "Tomek Nazar",
}


def seed_name_crossrefs(db: Session, mappings: dict[str, str] | None = None) -> int:
    """Upsert known name cross-references (idempotent on invoice_name). Returns rows inserted."""
    mappings = mappings or KNOWN_CROSSREFS
    added = 0
    for inv_name, clarity_name in mappings.items():
        existing = db.scalar(
            select(models.NameCrossref).where(models.NameCrossref.invoice_name == inv_name)
        )
        if existing:
            existing.clarity_name = clarity_name
        else:
            db.add(models.NameCrossref(invoice_name=inv_name, clarity_name=clarity_name))
            added += 1
    db.commit()
    return added


if __name__ == "__main__":
    from app.db.base import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        print(f"Seeded name cross-references (added {seed_name_crossrefs(db)}).")
    finally:
        db.close()
