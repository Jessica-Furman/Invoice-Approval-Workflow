"""Parse the sample invoice PDFs and print a field-level extraction report.

Usage:
  python -m app.services.parse_samples [folder]            # report only
  python -m app.services.parse_samples [folder] --store    # also store into the DB (shows in the UI)
"""
from __future__ import annotations

import glob
import os
import sys

from app.services.parsing import parse_invoice


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--store"]
    store = "--store" in sys.argv
    folder = args[0] if args else os.path.join("..", "contractor_invoices")
    pdfs = sorted(glob.glob(os.path.join(folder, "*.pdf")))
    if not pdfs:
        print(f"No PDFs in {folder}")
        return

    db = None
    if store:
        from app.db.base import SessionLocal, init_db
        init_db()
        db = SessionLocal()

    for path in pdfs:
        out = parse_invoice(path)
        if store:
            from app.services.ingestion import ingest_pdf
            inv = ingest_pdf(db, path)
            print(f"[stored invoice id={inv.id} status={inv.status}]")
        p = out.parsed
        print("=" * 78)
        print(f"{os.path.basename(path)}   [method={out.method}  confidence={out.confidence}  "
              f"has_text={out.has_text}]")
        print(f"  vendor_name        : {p.vendor_name}")
        print(f"  invoice_number     : {p.invoice_number}")
        print(f"  date_received      : {p.date_received}")
        print(f"  payment_period     : {p.payment_period}")
        print(f"  total_invoice_cost : {p.total_invoice_cost}")
        print(f"  line_items         : {len(p.line_items)}")
        for li in p.line_items[:4]:
            print(f"      - {li.contractor_name!r}  hours={li.hours}  rate={li.rate}  amount={li.amount}")
        if len(p.line_items) > 4:
            print(f"      … (+{len(p.line_items) - 4} more)")
        if out.missing_required():
            print(f"  MISSING REQUIRED   : {out.missing_required()}")
        for w in out.warnings:
            print(f"  ! {w}")

    if db is not None:
        db.close()


if __name__ == "__main__":
    main()
