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
