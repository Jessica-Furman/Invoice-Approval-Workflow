"""Import Clarity timesheet exports (User Stories 4-5).

The real Clarity "TimeEntry" export is granular (one row per resource/task/day). We aggregate hours
per (resource, period, investment) so each row is comparable to an invoice line, then idempotently
upsert keyed by a stable hash so re-imports don't create duplicates.

Distinct investments also populate `clarity_projects` (id + name); accounting fields (budget id,
CapEx/OpEx, cost center, spend) require the separate Clarity *project* export and stay null until then.

Usage (CLI):  python -m app.services.clarity_import "data/clarity/Clarity-TimeEntry ....csv"
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.utils.names import clarity_to_first_last, normalize_name

# Column names in the export -> our fields
COL_RESOURCE_ID = "Resource ID"
COL_RESOURCE_NAME = "Resource Name"
COL_RESOURCE_MANAGER = "Resource Manager"
COL_PERIOD_START = "Period Start Date"
COL_PERIOD_END = "Period Finish Date"
COL_INVESTMENT_ID = "Investment ID"
COL_INVESTMENT_NAME = "Investment Name"
COL_INVESTMENT_MANAGER = "Investment Manager"
COL_CHARGE_CODE = "Charge Code"
COL_TASK_NAME = "Task Name"
COL_TIMESHEET_STATUS = "Time Sheet Status"
COL_DATE_WORKED = "Date Worked"
COL_HOURS = "Time Entry Hours"

REQUIRED_COLUMNS = [
    COL_RESOURCE_NAME,
    COL_DATE_WORKED,
    COL_INVESTMENT_ID,
    COL_HOURS,
]

# Task-name variants that all mean paid time off (excluded from billable hours).
_TIME_OFF_RE = re.compile(r"time\s*off|\bpto\b", re.IGNORECASE)


def is_time_off(task_name: str | None) -> bool:
    """True for 'Time Off', 'timeoff', 'PTO', etc."""
    return bool(task_name) and bool(_TIME_OFF_RE.search(task_name))


def is_posted(status: str | None) -> bool:
    return (status or "").strip().lower() == "posted"


def classify_charge_code(charge_code: str | None) -> str | None:
    """Derive CapEx/OpEx from the Charge Code name (e.g. 'U0000-Upbound Capital' -> CAPEX,
    'X0000-Operating' -> OPEX). Returns 'CAPEX', 'OPEX', or None."""
    if not charge_code:
        return None
    cc = charge_code.lower()
    if "capital" in cc:
        return "CAPEX"
    if "operating" in cc:
        return "OPEX"
    return None


@dataclass
class ImportResult:
    source_rows: int = 0
    aggregated_rows: int = 0
    timesheets_created: int = 0
    timesheets_updated: int = 0
    projects_created: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "source_rows": self.source_rows,
            "aggregated_rows": self.aggregated_rows,
            "timesheets_created": self.timesheets_created,
            "timesheets_updated": self.timesheets_updated,
            "projects_created": self.projects_created,
            "warnings": self.warnings,
        }


def _to_date(value) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    ts = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(ts) else ts.date()


def _row_hash(resource_name: str, date_worked: str, investment_id: str, timeoff: bool, posted: bool) -> str:
    """Idempotency key for one aggregated timesheet row.

    `date_worked` MUST already be a canonical string (ISO 'YYYY-MM-DD'), never a raw source string:
    the CSV export writes dates like '5/11/26' while the live Clarity API returns
    '2026-05-11T00:00:00'. Hashing the raw text would make the same logical entry from the two
    sources hash differently and duplicate — doubling a contractor's hours during matching.
    """
    key = f"{normalize_name(resource_name)}|{date_worked}|{investment_id}|{int(timeoff)}|{int(posted)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def _read_table(path: str) -> pd.DataFrame:
    """Read a Clarity export as CSV or Excel, tolerant of Windows (cp1252) encodings."""
    lower = path.lower()
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(path, dtype=str)
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding=enc)
        except UnicodeDecodeError:
            continue
    # Last resort: replace undecodable bytes so the import still proceeds.
    return pd.read_csv(
        path, dtype=str, keep_default_na=False, na_values=[""],
        encoding="utf-8", encoding_errors="replace",
    )


def import_timesheets(db: Session, csv_path: str) -> ImportResult:
    """Import a Clarity TimeEntry CSV/Excel export from disk (the manual-upload path)."""
    df = _read_table(csv_path)
    return import_dataframe(db, df)


def import_dataframe(db: Session, df: pd.DataFrame) -> ImportResult:
    """Aggregate + idempotently upsert a Clarity TimeEntry table already loaded into a DataFrame.

    Source-agnostic core shared by the CSV upload path (`import_timesheets`) and the live Clarity
    API sync path (`clarity_sync.py`) — both just need to produce a DataFrame with these columns.
    """
    result = ImportResult()
    result.source_rows = len(df)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Clarity export is missing required columns: {missing}")

    df[COL_HOURS] = pd.to_numeric(df[COL_HOURS], errors="coerce").fillna(0.0)

    # Time-off flag (Time Off / timeoff / PTO) — excluded from billable hours during matching.
    df["_timeoff"] = (
        df[COL_TASK_NAME].fillna("").str.contains(_TIME_OFF_RE)
        if COL_TASK_NAME in df.columns
        else False
    )
    # Posted flag — only "Posted" timesheets count.
    df["_posted"] = (
        df[COL_TIMESHEET_STATUS].fillna("").str.strip().str.lower().eq("posted")
        if COL_TIMESHEET_STATUS in df.columns
        else True
    )

    # Aggregate to DATE level so hours can later be filtered to an invoice's exact period, and so
    # time-off / non-posted can be separated. Group by resource + date + investment + flags.
    group_cols = [COL_RESOURCE_NAME, COL_DATE_WORKED, COL_INVESTMENT_ID, "_timeoff", "_posted"]
    # groupby(dropna=False) still drops a group if ANY key is NaN; fill keys so every row is retained.
    for c in [COL_RESOURCE_NAME, COL_DATE_WORKED, COL_INVESTMENT_ID]:
        df[c] = df[c].fillna("")
    agg_spec = {"hours": (COL_HOURS, "sum")}
    carry = {
        "resource_id": COL_RESOURCE_ID,
        "resource_manager": COL_RESOURCE_MANAGER,
        "investment_name": COL_INVESTMENT_NAME,
        "investment_manager": COL_INVESTMENT_MANAGER,
        "charge_code": COL_CHARGE_CODE,
        "task_name": COL_TASK_NAME,
        "time_sheet_status": COL_TIMESHEET_STATUS,
        "period_start": COL_PERIOD_START,
        "period_end": COL_PERIOD_END,
    }
    for out_name, src_col in carry.items():
        if src_col in df.columns:
            agg_spec[out_name] = (src_col, "first")

    agg = df.groupby(group_cols, dropna=False).agg(**agg_spec).reset_index()
    result.aggregated_rows = len(agg)

    # Per-project CapEx/OpEx + name, derived across the whole file (Charge Code drives the type).
    type_by_proj: dict[str, str] = {}
    name_by_proj: dict[str, str] = {}
    inv = df[df[COL_INVESTMENT_ID] != ""].copy()
    if not inv.empty:
        if COL_CHARGE_CODE in inv.columns:
            inv["_type"] = inv[COL_CHARGE_CODE].map(classify_charge_code)
            typed = inv.dropna(subset=["_type"])
            if not typed.empty:
                type_by_proj = (
                    typed.groupby(COL_INVESTMENT_ID)["_type"]
                    .agg(lambda s: s.value_counts().idxmax())
                    .to_dict()
                )
        if COL_INVESTMENT_NAME in inv.columns:
            names = inv.dropna(subset=[COL_INVESTMENT_NAME])
            if not names.empty:
                name_by_proj = names.groupby(COL_INVESTMENT_ID)[COL_INVESTMENT_NAME].first().to_dict()

    # Existing timesheets keyed by hash (one query, avoids N+1).
    existing = {
        ts.source_row_hash: ts
        for ts in db.scalars(select(models.ClarityTimesheet)).all()
        if ts.source_row_hash
    }
    existing_projects = {
        p.project_id: p
        for p in db.scalars(select(models.ClarityProject)).all()
        if p.project_id
    }

    # Coerce pandas NaN -> None so empty Investment IDs don't create phantom projects each run.
    records = agg.where(pd.notnull(agg), None).to_dict("records")
    for rd in records:
        resource_name = rd[COL_RESOURCE_NAME]
        investment_id = rd[COL_INVESTMENT_ID] or None  # "" sentinel -> None
        date_worked = _to_date(rd[COL_DATE_WORKED])
        timeoff = bool(rd["_timeoff"])
        posted = bool(rd["_posted"])
        # Hash on the CANONICAL parsed date (ISO), not the raw source string, so a row from the CSV
        # export and the same row from the Clarity API collapse to one entry instead of duplicating.
        h = _row_hash(
            resource_name,
            date_worked.isoformat() if date_worked else "",
            investment_id or "",
            timeoff,
            posted,
        )

        display_name = clarity_to_first_last(resource_name)
        charge_code = rd.get("charge_code")
        fields = dict(
            contractor_name=display_name,
            contractor_name_normalized=normalize_name(resource_name),
            hours=round(float(rd["hours"]), 2),
            rate=None,
            date_worked=date_worked,
            is_time_off=timeoff,
            task_name=rd.get("task_name"),
            time_sheet_status=rd.get("time_sheet_status"),
            is_posted=posted,
            period_start=_to_date(rd.get("period_start")),
            period_end=_to_date(rd.get("period_end")),
            project_id=investment_id,
            resource_id=rd.get("resource_id"),
            resource_manager=rd.get("resource_manager"),
            investment_name=rd.get("investment_name"),
            investment_manager=rd.get("investment_manager"),
            charge_code=charge_code,
            capex_opex=classify_charge_code(charge_code),
            source_row_hash=h,
        )

        if h in existing:
            ts = existing[h]
            for k, v in fields.items():
                setattr(ts, k, v)
            result.timesheets_updated += 1
        else:
            ts = models.ClarityTimesheet(**fields)
            db.add(ts)
            existing[h] = ts
            result.timesheets_created += 1

    # Projects: distinct investments, enriched with derived CapEx/OpEx + name.
    for pid in set(name_by_proj) | set(type_by_proj):
        proj = existing_projects.get(pid)
        if proj is None:
            proj = models.ClarityProject(project_id=pid)
            db.add(proj)
            existing_projects[pid] = proj
            result.projects_created += 1
        if not proj.project_name and name_by_proj.get(pid):
            proj.project_name = name_by_proj[pid]
        if not proj.capex_opex and type_by_proj.get(pid):
            proj.capex_opex = type_by_proj[pid]

    db.commit()
    return result


def _main() -> None:
    import sys

    from app.db.base import SessionLocal, init_db

    if len(sys.argv) < 2:
        print('Usage: python -m app.services.clarity_import "<path-to-clarity.csv>"')
        raise SystemExit(2)

    init_db()
    db = SessionLocal()
    try:
        res = import_timesheets(db, sys.argv[1])
        print("Clarity import complete:")
        for k, v in res.as_dict().items():
            print(f"  {k}: {v}")
    finally:
        db.close()


if __name__ == "__main__":
    _main()
