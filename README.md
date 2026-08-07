# InVoicee — Contractor Invoice Processing System

Automates contractor invoice processing for Upbound Group: parse contractor invoice PDFs, match them
against **Clarity** timekeeping data, route matched vs. flagged invoices, and generate a **Coupa** import
CSV — all on a 3-column dashboard (Flagged | Matched | All).

Built **local-first**: SQLite and local folders stand in for Postgres / Outlook / S3, so it runs with no
cloud credentials except an optional Clarity API key. This README is a handoff guide — read it start to
finish before touching code if you're new to the project.

> **Full engineering details live in [`CLAUDE.md`](./CLAUDE.md)** — matching rules, parsing approach,
> Clarity realities, and conventions. That file is written for Claude Code but is equally useful for a
> human developer; treat it as the technical reference and this README as the onboarding map.

## Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (SQLite locally; Postgres-ready via `DATABASE_URL`)
- **Frontend:** React + Vite + TypeScript + Tailwind
- **DB:** SQLite for dev (`data/invoicee.sqlite3`); Postgres via `docker-compose.yml` when available

## Where things are

| Path | What |
|---|---|
| `backend/app/` | FastAPI app — `models/`, `services/` (parsing, matching, routing, coupa, clarity_import, clarity_api, approval, export_excel), `api/` routers |
| `frontend/src/` | React dashboard (Vite + TS + Tailwind) |
| `data/` | Local mock tree — git-ignored. `data/clarity/` (Clarity CSV/Excel exports), `data/inbox/{matched,flagged}` (routed PDFs), `data/storage/` (mock S3 output — never put input files here), `data/invoicee.sqlite3` (the DB) |
| `contractor_invoices/` | Sample contractor invoice PDFs — the pipeline's real input folder |
| `documentation/` | User stories, Figma exports, Coupa CSV template/rules (`csv_rules`, `CSV creation blueprint.csv`, `Final CSV.txt`, `Coupa sample invoice.xlsx`), Clarity screenshots, `Active supplier list.csv`, `Company_by_Project.csv`, `Budget_ID's.xlsx`, architecture doc |
| `.claude/plans/` | The original milestone build plan (M1–M9) |
| `.env` / `.env.example` | Local config — see below. `.env` is git-ignored; never commit it |
| `start.ps1` | Launches backend + frontend + opens the browser in one step |

## Getting set up on a new machine

### Prerequisites
- Python 3.11+
- **Node is not on PATH by default if installed via winget (user-scope).** If `node`/`npm` aren't found:
  ```powershell
  $env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64;$env:Path"
  ```
- **No Docker / no admin rights assumed.** Everything below runs on SQLite with no elevated permissions.
  Postgres via `docker-compose.yml` is supported but optional (see bottom of this file).

### 1. Copy `.env`
Copy `.env` from the old machine (or from `.env.example` and fill in real values) to the repo root.
Minimum to run locally: `DATABASE_URL` (defaults fine for SQLite) and the local mock-path vars. Optional:
- `ANTHROPIC_API_KEY` — LLM parser fallback. **Currently unused/disabled by design**; rules + OCR cover
  all known sample formats. Leave blank unless you're specifically re-enabling it.
- `CLARITY_API_URL` / `CLARITY_API_CLIENT_ID` / `CLARITY_API_KEY` — live Clarity REST sync on invoice
  upload. If unset, the app runs fine on manually-uploaded Clarity CSV/Excel exports instead.

### 2. Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Build the DB from REAL data (drops tables -> imports newest data/clarity export ->
# parses contractor_invoices/ -> matches -> routes). This is the preferred way to get a working DB.
.\.venv\Scripts\python.exe -m app.bootstrap

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000   # API + docs at /docs
```
**Do not run `app.seed`** — it loads fake demo data that pollutes the board. Always use `app.bootstrap`.

### 3. Frontend
```powershell
cd frontend
npm install
npm run dev     # http://localhost:5173
```

Or from the repo root, `.\start.ps1` launches both and opens the browser.

Open http://localhost:5173 for the 3-column dashboard. Click a card to open the side-by-side
Invoice vs. Clarity detail view.

### Iterating without a full rebuild
The full `app.bootstrap` re-imports ~84k Clarity rows and is slow. If you're only changing
parsing/matching/routing code, stop the backend first (SQLite is single-writer — see below), then:
```powershell
.\.venv\Scripts\python.exe -m app.services.parse_samples ..\contractor_invoices --store
.\.venv\Scripts\python.exe -m app.services.matching
.\.venv\Scripts\python.exe -m app.services.routing
```

### Tests
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

### Frontend type-check
```powershell
cd frontend
npm run build    # runs tsc -b && vite build — use this to catch TS errors before shipping
```

## Critical gotcha: SQLite is single-writer

Stop the backend (kill the process on port 8000) before running `bootstrap`, `parse_samples --store`,
`matching`, or `routing` — any command that writes or recreates tables. Running them while `uvicorn` is
up will lock the database.

```powershell
# find and kill whatever is holding port 8000 (PowerShell)
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
```

## The processing pipeline (mental model)

Every invoice flows through four service stages under `backend/app/services/`, each independently
testable and driven by both CLIs and API endpoints:

1. **Parse** (`parsing/parser.py`) — regex header extraction + `pdfplumber` table extraction for line
   items, OCR fallback (`rapidocr-onnxruntime`, offline) for scanned PDFs. LLM fallback exists but is
   intentionally disabled.
2. **Ingest** (`ingestion.py`) — stores the PDF (mock S3), upserts `Invoice` + line items (idempotent on
   invoice number), resolves the invoice period.
3. **Match** (`matching.py`) — resolves each contractor to a Clarity person, compares hours against
   posted (non-time-off) Clarity entries within the invoice's date window. **The matching rules are
   user-specified and detailed exactly in `CLAUDE.md` — do not change them without explicit sign-off.**
4. **Route** (`routing.py`) — copies the PDF into `data/inbox/{matched,flagged}/`, sets `routed_to`,
   writes an audit log row.

A parallel, simpler pipeline exists for **non-contractor invoices** (hardware/software/subscription,
"Other Invoice Types" tab) — same PDF-parsing tooling, no Clarity matching, no Coupa CSV. Kept fully
separate from the contractor pipeline in both backend routing and the DB (`Invoice.invoice_type`).

## Current status (see `.claude/plans/` for the original milestone plan)

Milestones M1–M9 are complete: skeleton + dashboard, Clarity CSV import, hybrid PDF parsing, matching
engine, routing, Coupa CSV generation (full 177/73-column template, per-project split, supplier-number
lookup, chart-of-accounts for matched invoices), manual-review actions, and the "Other Invoice Types"
pipeline. Remaining open items, if you pick this back up:
- **Requester Email/Name and Account Code** in the Coupa CSV are still blank placeholders — blocked on
  an approval-chain/vendor-mapping decision that was never finalized.
- Coupa CSV generation is manual-download only (phase 1 of a staged plan); routing the CSV into an
  actual Coupa ingest folder and full automation were never started.
- M8 (swap `LocalStorage`→S3 and the local inbox→Microsoft Graph) was never done — everything still
  runs against local folders. There's no cloud credential wiring to worry about breaking.

## Switching to Postgres (optional, not required for local dev)
1. Install Docker Desktop, then `docker compose up -d`.
2. Set `DATABASE_URL=postgresql+psycopg2://invoicee:invoicee@localhost:5432/invoicee` in `.env`.
3. Re-run `app.bootstrap`.

## If something looks wrong
Check `CLAUDE.md` first — it documents non-obvious business rules (matching tolerances, period-priority
logic, Clarity's lack of a rate column, CapEx/OpEx derivation) that are easy to "fix" incorrectly if you
don't know they're intentional.
