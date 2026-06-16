# InVoicee — Contractor Invoice Processing System

Automates contractor invoice processing for Upbound Group: ingest invoices, parse the required fields,
match them against Clarity timesheet + project data, route matched vs. flagged invoices, and generate a
Coupa-ready CSV — all on a clean 3-column dashboard.

Built **local-first**: SQLite + local folders stand in for Postgres / Outlook / S3 so it runs with no
cloud credentials. See `.claude/plans/` for the full build plan and milestones (M1–M8).

## Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (SQLite locally, Postgres-ready)
- **Frontend:** React + Vite + TypeScript + Tailwind
- **DB:** SQLite for dev (`data/invoicee.sqlite3`); Postgres via `docker-compose.yml` when available

## Quick start

### 1. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows PowerShell:  .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed                # create tables + load demo data
uvicorn app.main:app --reload     # http://localhost:8000  (docs at /docs)
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

Open http://localhost:5173 to see the 3-column dashboard (Flagged | Matched | All). Click any card to
open the side-by-side Invoice vs. Clarity detail view.

## Switching to Postgres (later)
1. Install Docker Desktop, then `docker compose up -d`.
2. Set `DATABASE_URL=postgresql+psycopg2://invoicee:invoicee@localhost:5432/invoicee` in `.env`.
3. Re-run `python -m app.seed`.

## Repo layout
- `backend/` — FastAPI app, models, services (ingestion, parsing, matching, routing, coupa…)
- `frontend/` — Vite/React dashboard
- `data/` — local mock tree (inbox folders, mock S3 storage, Clarity exports) — git-ignored
- `documentation/` — user stories, Figma designs, Coupa CSV template (`Final CSV.txt`), Clarity screenshots
- `contractor_invoices/` — 5 sample invoice PDFs


## Milestones (each is an independently testable win)

### M1 — Runnable skeleton + UI you can click (fastest visible win)
- `docker-compose up` Postgres; FastAPI boots with `/health`; Alembic creates schema.
- Seed script loads mock invoices/line items/Clarity/projects so the board is populated.
- React dashboard renders the 3 columns (Flagged | Matched | All) with `InvoiceCard`s and the
  `DetailDrawer` showing Invoice vs. Clarity side-by-side + project table (matches Figma).
- **Test:** `docker-compose up` + `npm run dev` → board shows seeded cards; clicking a card opens the
  side-by-side detail. `pytest` green for `/health` and seed.

### M2 — Clarity import (User Stories 4–5)
- `clarity_import.py` loads timesheet + project CSV/Excel (`pandas`), normalizes names, idempotent upsert.
- `POST /clarity/import` endpoint + a simple upload control in the UI.
- **Test:** import sample exports twice → no duplicates; rows queryable via `/clarity/*`.

### M3 — Ingestion + storage + hybrid parsing (User Stories 1–3, 26–27)
- `LocalFolderInbox` watches `data/inbox/contractor_invoices/` (`watchdog`); new PDF → `LocalStorage`
  (mock S3) → `invoices` row with `pdf_storage_key`.
- `parsing/`: `rules.py` (`pdfplumber`) extracts fields/line items; low confidence or missing required
  fields → `llm.py` Claude fallback returns the JSON contract. Failures → `processing_failed`; missing
  fields → `needs_manual_review` with reasons.
- **Test:** drop the 5 sample PDFs in the folder → rows created, PDFs in mock storage, fields parsed;
  a deliberately bad PDF → `processing_failed` without crashing. Parser eval over samples in `pytest`.

### M4 — Matching engine + cross-reference (User Stories 6–11)
- Name resolution: direct → normalized → `rapidfuzz` fuzzy → `name_crossref`; unresolved → flagged.
- Per line item compare hours, rate, computed total vs. Clarity (tolerance configurable); store diffs;
  derive invoice status; persist mismatch reasons.
- **Test:** seeded matching cases (clean match, name variant via crossref, hours/rate/total mismatch)
  produce the expected statuses and diffs.

### M5 — Routing + live UI wiring (User Stories 12–16)
- `routing.py` moves the PDF `contractor_invoices → matched/ | flagged/` per status; logs to `audit_log`.
- Dashboard reads real data; flagged cards highlight the offending field (name/hours/rate/total/period/missing).
- **Test:** end-to-end — drop PDFs → cards land in correct columns, files moved, flagged card shows the
  failing field highlighted side-by-side.

### M6 — Coupa CSV + approval chain + Excel export (User Stories 19–23)
- `approval.py` resolves first approver (vendor mapping → project mapping → else flag).
- `coupa.py` builds the CSV per the user-provided spec (invoice + Clarity + project + first approver);
  "Approved, create CSV" button enabled only for matched invoices; blocked for flagged (US 21).
- `export_excel.py` exports invoice/Clarity/project review data (single + multi).
- **Test:** matched invoice → valid CSV matching the spec columns; flagged invoice → CSV blocked with
  reason; Excel export opens with all sections.

### M7 — Manual review actions + audit (User Stories 17–18, 24–25, 28–29)
- Mark-as-matched, reprocess (rerun parse→match→route), edit name/project-manager mappings in `Mappings.tsx`.
- Full audit trail of received/parsed/matched/routed/CSV/manual events.
- **Test:** flag → add crossref mapping → reprocess → moves to matched; audit log shows the sequence.

### M8 — Swap mocks for real integrations (post-demo)
- Implement `S3Storage` (`boto3`) and `GraphInbox` (Microsoft Graph via `msal`) behind existing
  interfaces; switch via config. No business-logic changes.
- **Test:** integration tests against a real test inbox + bucket; same end-to-end flow passes.