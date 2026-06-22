"""Rebuild the database from REAL data only (no demo/seed rows).

Steps:
  1. Drop & recreate all tables (empty).
  2. Import the newest Clarity export found in data/clarity (or a path you pass).
  3. Parse & store every PDF in contractor_invoices/.
  4. Run name+hours matching.

Usage:
  python -m app.bootstrap
  python -m app.bootstrap "..\\data\\clarity\\Clarity-TimeEntry ....csv" "..\\contractor_invoices"
"""
from __future__ import annotations

import glob
import os
import sys

import app.models  # noqa: F401  -- registers tables on Base.metadata so drop_all/create_all work
from app.config import settings
from app.db.base import Base, SessionLocal, engine


def _newest_clarity_file() -> str | None:
    candidates = [
        f for f in glob.glob(os.path.join(settings.CLARITY_DIR, "*"))
        if f.lower().endswith((".csv", ".xlsx", ".xls"))
    ]
    return max(candidates, key=os.path.getmtime) if candidates else None


def main() -> None:
    clarity_path = sys.argv[1] if len(sys.argv) > 1 else _newest_clarity_file()
    invoice_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join("..", "contractor_invoices")

    print("1) Resetting database (dropping demo + all data) ...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if clarity_path and os.path.exists(clarity_path):
            print(f"2) Importing Clarity export: {os.path.basename(clarity_path)}")
            from app.services.clarity_import import import_timesheets

            res = import_timesheets(db, clarity_path)
            print(f"   timesheets={res.timesheets_created} projects={res.projects_created}")
        else:
            print("2) No Clarity export found in data/clarity — skipping (matching will find nothing).")

        print(f"3) Parsing invoices in {invoice_dir} ...")
        from app.services.ingestion import ingest_pdf

        pdfs = sorted(glob.glob(os.path.join(invoice_dir, "*.pdf")))
        for pdf in pdfs:
            inv = ingest_pdf(db, pdf)
            print(f"   {os.path.basename(pdf)} -> invoice {inv.id} "
                  f"({inv.invoice_number}, {len(inv.line_items)} lines, {inv.status})")

        print("3b) Seeding confirmed name cross-references ...")
        from app.services.name_crossref_seed import seed_name_crossrefs

        print(f"   crossrefs added: {seed_name_crossrefs(db)}")

        print("4) Matching invoices against Clarity ...")
        from app.services.matching import match_all

        counts = match_all(db)
        print(f"   results: {counts}")

        print("5) Routing invoices to matched/flagged inboxes ...")
        from app.services.routing import route_all

        print(f"   routed: {route_all(db)}")
        print("Done. Start the API and refresh the UI.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
