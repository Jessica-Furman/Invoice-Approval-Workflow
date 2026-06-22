# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

InVoicee automates contractor invoice processing for Upbound Group: parse contractor invoice PDFs,
match them against **Clarity** timekeeping data, route matched vs. flagged invoices, and (planned)
generate a **Coupa** import CSV — all on a 3-column dashboard (Flagged | Matched | All). It is built
**local-first**: SQLite and local folders stand in for Postgres / Outlook / S3 so it runs with no cloud
credentials. The full milestone plan lives in `.claude/plans/i-m-trying-to-build-inherited-gosling.md`.

## Environment constraints (important)

- **No Docker, no admin rights.** Postgres-via-docker is unavailable; local dev runs on **SQLite**
  (`data/invoicee.sqlite3`). Models use SQLAlchemy generic `JSON` columns so the schema is Postgres-ready
  — switching is just `DATABASE_URL` in `.env` (a `docker-compose.yml` for Postgres 16 is provided).
- **Node is installed user-scope** (winget). If `node`/`npm` aren't found, prepend to PATH:
  `$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64;$env:Path"`
- Shell is PowerShell. Always run backend Python via the venv interpreter: `backend\.venv\Scripts\python.exe`.
- **SQLite is single-writer**: stop the backend (kill the PID on port 8000) before any command that
  drops/recreates tables or writes (bootstrap, seed, parse `--store`, matching, routing), or it will lock.

## Common commands

```powershell
# --- backend setup (once) ---
cd backend; python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt

# --- rebuild the DB from REAL data (preferred reset) ---
# drops tables -> imports newest data/clarity export -> parses contractor_invoices/ -> matches -> routes
.\.venv\Scripts\python.exe -m app.bootstrap

# --- faster iteration when only parsing/matching code changed (skips the ~84k-row Clarity re-import) ---
.\.venv\Scripts\python.exe -m app.services.parse_samples ..\contractor_invoices --store
.\.venv\Scripts\python.exe -m app.services.matching
.\.venv\Scripts\python.exe -m app.services.routing

# --- run servers ---
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000   # API + docs at /docs
cd ..\frontend; npm install; npm run dev                                          # UI at :5173
# or from repo root: .\start.ps1   (launches both + opens the browser)

# --- tests ---
cd backend; .\.venv\Scripts\python.exe -m pytest tests/ -q
.\.venv\Scripts\python.exe -m pytest tests/test_matching.py::test_exact_match_sets_matched -q   # single test

# --- frontend type-check / production build ---
cd frontend; npm run build    # runs `tsc -b && vite build`; use this to catch TS errors
```

`app.seed` exists but loads FAKE demo data — **do not use it**; it pollutes the board. Use `app.bootstrap`.

## Architecture: the processing pipeline

Each invoice flows through stages, each a service under `backend/app/services/`. The same functions are
driven both by CLIs (`bootstrap.py`, `parse_samples.py`, module `__main__`s) and by API endpoints, so
business logic lives in services, not routes.

1. **Parse** (`parsing/parser.py: parse_invoice`) — orchestrates `rules.py` → `ocr.py` (scanned PDFs) →
   `llm.py`. **LLM is intentionally disabled** (no `ANTHROPIC_API_KEY`); prefer rules + OCR. `rules.py`
   extracts headers via regex and line items via pdfplumber **table extraction** (raw text mangles
   numbers), with a text-layout fallback (`parse_rate_list_text`) and OCR-text block parser. OCR uses
   `rapidocr-onnxruntime` + `pypdfium2` (offline, no system binary).
2. **Ingest** (`ingestion.py: ingest_pdf`) — stores the PDF via `storage.LocalStorage` (mock S3), upserts
   an `Invoice` + `invoice_line_items` (idempotent on invoice number), and resolves the invoice period
   (see "period priority" below).
3. **Match** (`matching.py: match_all`/`match_invoice`) — resolves each contractor to a Clarity person and
   compares hours. See the matching rules below — they are user-specified and must be followed exactly.
4. **Route** (`routing.py: route_all`) — copies the PDF into `data/inbox/{matched,flagged}/` per status
   (mocks Outlook), sets `Invoice.routed_to`, and writes an `audit_log` row.

`storage/` and the inbox folders are interface seams: M8 swaps `LocalStorage`→S3 (boto3) and the
local-folder inbox→Microsoft Graph without touching callers.

## Data model & Clarity realities

ORM models are all in `backend/app/models/__init__.py`. Key facts that drive the logic:

- `clarity_timesheets` rows are **date-level** (one per resource/Date Worked/investment/time-off/posted),
  not pay-period aggregates — this enables filtering hours to an invoice's exact window. Import is in
  `clarity_import.py` (idempotent via `source_row_hash`).
- The real Clarity export (`data/clarity/*.csv`) is "Last, First" names, **has no pay-rate column**, and
  CapEx/OpEx is derived from the "Charge Code" text ("capital"→CAPEX, "operating"→OPEX). The separate
  Clarity **project** export (budget id / cost center / spend) is not yet available.
- `invoice_line_items` keep thin typed columns plus an `extra` JSON (holds per-line period_start/end);
  `diff` JSON holds match results shown in the UI.

## Matching rules (user-specified — change only on explicit instruction)

In `matching.py` (`ClarityIndex.resolve`, `_clarity_hours_for`, `match_invoice`):

- **Name resolution**: exact normalized → **order-insensitive** (sorted tokens, so invoice "First Last"
  matches Clarity "Last, First") → `name_crossref` table → fuzzy `rapidfuzz.token_sort_ratio` **≥ 80**.
- **Clarity hours counted**: only `is_posted` (Time Sheet Status == "Posted"), **excluding** time off
  (`Task Name` ~ "time off"/"timeoff"/"PTO"), and only entries whose **Date Worked** is within the
  invoice period. Rate is **not** validated (Clarity has no rate).
- **Hours tolerance**: `max(1.0 hour, 2%)`. Invoice is `matched` only if every line matches.
- **Single-contractor invoices**: when *all* lines resolve to the *same one* person, compare the **summed**
  invoice hours to that person's Clarity total. All other (multi-contractor) invoices match **per line**.
- **Invoice period priority** (`ingestion.py`, critical): a **labeled** "Period:" header wins (handles
  per-line date typos) → else the **full span of line-item periods** (handles scanned invoices with no
  header period) → else an unlabeled header date range.
- Dates parse American or European (`DD/MM/YYYY`): first number > 12 ⇒ day-first; ambiguous ⇒ American.

## Conventions

- Input invoices go in `contractor_invoices/` (the pipeline reads this). `data/storage/` is mock-S3 OUTPUT
  — do not put inputs there.
- Add a focused pytest for new parsing/matching behavior; tests construct their own in-memory/temp SQLite
  and don't need a running server. Sample-PDF tests `skipif` the file is absent.
- Backend serves the UI cross-origin; CORS origins for the Vite dev server are set in `config.py`.
