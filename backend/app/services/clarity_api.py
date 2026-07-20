"""Live Clarity timesheet API client (Broadcom Clarity PPM REST API v1).

Auth is key-based (no login/session step): the `x-api-ppm-client` header carries the client ID,
`Authorization: Bearer <key>` carries the API key — confirmed against Broadcom's public TechDocs
and by a live read-only call against the dev tenant.

Data is nested three levels deep: a timesheet (one per resource/week) has a `timeEntries` list (one
per investment/task the resource logged that week), and each time entry has a day-by-day `actuals`
curve (hours in *seconds*). So building one CSV-equivalent row per (resource, date, investment)
means: resolve each contractor name to a Clarity resourceId, list their timesheets in the invoice's
period, then drill into each timesheet's time entries for investment/task/day-level hours. This is
several HTTP round-trips per contractor — acceptable for a per-invoice-upload sync (a handful of
contractors, a narrow date window), not for a full-catalog pull (hence CSV import stays how you'd
backfill/refresh everything at once).
"""
from __future__ import annotations

from datetime import date

import httpx
import pandas as pd

from app.config import settings

RESOURCES_PATH = "/ppm/rest/v1/resources"
TIMESHEETS_PATH = "/ppm/rest/v1/timesheets"


def is_configured() -> bool:
    return bool(settings.CLARITY_API_URL and settings.CLARITY_API_CLIENT_ID and settings.CLARITY_API_KEY)


def _headers() -> dict[str, str]:
    return {
        "x-api-ppm-client": settings.CLARITY_API_CLIENT_ID,
        "Authorization": f"Bearer {settings.CLARITY_API_KEY}",
        "Accept": "application/json",
    }


def _get(client: httpx.Client, path: str, params: dict | None = None) -> dict:
    response = client.get(path, params=params)
    response.raise_for_status()
    return response.json()


def _first_last_to_clarity(name: str) -> str:
    """'Julian Sanchez' -> 'Sanchez, Julian' (Clarity's resource `fullName` filter format)."""
    parts = name.strip().split()
    if len(parts) < 2:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _resolve_resource_id(client: httpx.Client, name: str) -> int | None:
    """Look up a Clarity resourceId for an invoice contractor name. Returns None (not raises) when
    not found — a contractor with no Clarity resource yet is a normal, expected case that matching
    already treats as 'unresolved', not an API failure."""
    for candidate in dict.fromkeys([_first_last_to_clarity(name), name]):
        data = _get(client, RESOURCES_PATH, {"filter": f"(fullName = '{candidate}')"})
        results = data.get("_results", [])
        if results:
            return results[0]["_internalId"]
    return None


def _fmt(d: date) -> str:
    return f"{d.isoformat()}T00:00:00"


def _timesheet_rows(client: httpx.Client, resource_id: int, start: date | None, end: date | None) -> list[dict]:
    filter_expr = f"(resourceId = {resource_id})"
    if start:
        filter_expr += f" and (timePeriodStart >= '{_fmt(start)}')"
    if end:
        filter_expr += f" and (timePeriodFinish <= '{_fmt(end)}')"

    rows: list[dict] = []
    ts_list = _get(client, TIMESHEETS_PATH, {"filter": filter_expr, "limit": 100})
    for ts_ref in ts_list.get("_results", []):
        ts_id = ts_ref["_internalId"]
        ts = _get(client, f"{TIMESHEETS_PATH}/{ts_id}")
        status = (ts.get("status") or {}).get("displayValue")
        resource_name = ts.get("resourceName")
        resource_manager = ts.get("resourceManager")
        period_start = ts.get("timePeriodStart")
        period_finish = ts.get("timePeriodFinish")

        te_list = _get(client, f"{TIMESHEETS_PATH}/{ts_id}/timeEntries")
        for te_ref in te_list.get("_results", []):
            te = _get(client, f"{TIMESHEETS_PATH}/{ts_id}/timeEntries/{te_ref['_internalId']}")
            charge_code = (te.get("chargeCode") or {}).get("displayValue")
            segments = ((te.get("actuals") or {}).get("segmentList") or {}).get("segments", [])
            for seg in segments:
                hours = (seg.get("value") or 0) / 3600
                if hours <= 0:
                    continue
                rows.append(
                    {
                        "Resource Name": resource_name,
                        "Resource Manager": resource_manager,
                        "Time Sheet Status": status,
                        "Period Start Date": period_start,
                        "Period Finish Date": period_finish,
                        "Investment ID": te.get("investmentCode"),
                        "Investment Name": te.get("investmentName"),
                        "Investment Manager": None,
                        "Charge Code": charge_code,
                        "Task Name": te.get("taskName"),
                        "Date Worked": seg.get("start"),
                        "Time Entry Hours": hours,
                    }
                )
    return rows


def fetch_timesheets(
    contractor_names: list[str], start: date | None, end: date | None
) -> pd.DataFrame:
    """Fetch Clarity TimeEntry rows for the given contractors/period as a DataFrame shaped like the
    CSV export (same column names `clarity_import.import_dataframe` expects). Raises on any failure
    — never swallows errors, that's `clarity_sync.py`'s job."""
    if not is_configured():
        raise RuntimeError(
            "Clarity API is not configured (CLARITY_API_URL/CLARITY_API_CLIENT_ID/CLARITY_API_KEY unset)"
        )

    rows: list[dict] = []
    with httpx.Client(
        base_url=settings.CLARITY_API_URL.rstrip("/"),
        headers=_headers(),
        timeout=settings.CLARITY_API_TIMEOUT_SECONDS,
    ) as client:
        for name in contractor_names:
            resource_id = _resolve_resource_id(client, name)
            if resource_id is None:
                continue
            rows.extend(_timesheet_rows(client, resource_id, start, end))

    return pd.DataFrame(rows)
