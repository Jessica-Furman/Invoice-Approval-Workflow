"""Tests for the live Clarity REST API client (`clarity_api.fetch_timesheets`).

Mocks the transport layer (not `fetch_timesheets` itself) so the resource-resolution -> timesheet
list -> timeEntries drill-down logic is actually exercised, using response shapes captured from a
real read-only call against the dev tenant (see the Clarity API integration plan)."""
from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.config import settings
from app.services import clarity_api


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == clarity_api.RESOURCES_PATH:
        return httpx.Response(200, json={
            "_results": [{"_internalId": 5073403, "fullName": "Sanchez, Julian"}]
        })
    if path == clarity_api.TIMESHEETS_PATH:
        return httpx.Response(200, json={"_results": [{"_internalId": 5150555}]})
    if path == f"{clarity_api.TIMESHEETS_PATH}/5150555":
        return httpx.Response(200, json={
            "status": {"displayValue": "Posted"},
            "resourceName": "Sanchez, Julian",
            "resourceManager": "Vaidya, Avani",
            "timePeriodStart": "2026-02-09T00:00:00",
            "timePeriodFinish": "2026-02-13T00:00:00",
        })
    if path == f"{clarity_api.TIMESHEETS_PATH}/5150555/timeEntries":
        return httpx.Response(200, json={"_results": [{"_internalId": 5181715}]})
    if path == f"{clarity_api.TIMESHEETS_PATH}/5150555/timeEntries/5181715":
        return httpx.Response(200, json={
            "investmentCode": "PR00433",
            "investmentName": "Acima Mobile App - Training and Development",
            "taskName": "New hire onboarding",
            "chargeCode": {"displayValue": "X0000-Operating"},
            "actuals": {
                "segmentList": {
                    "segments": [
                        {"start": "2026-02-08T00:00:00", "value": 0},
                        {"start": "2026-02-09T00:00:00", "value": 28800},
                    ]
                }
            },
        })
    raise AssertionError(f"Unexpected request: {request.method} {path}")


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setattr(settings, "CLARITY_API_URL", "https://clarity.example")
    monkeypatch.setattr(settings, "CLARITY_API_CLIENT_ID", "Upbound")
    monkeypatch.setattr(settings, "CLARITY_API_KEY", "test-key")


def test_fetch_timesheets_resolves_and_flattens(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(_handler), **kw),
    )

    df = clarity_api.fetch_timesheets(["Julian Sanchez"], date(2026, 2, 1), date(2026, 2, 28))

    assert len(df) == 1  # the 0-hour segment is excluded
    row = df.iloc[0]
    assert row["Investment ID"] == "PR00433"
    assert row["Task Name"] == "New hire onboarding"
    assert row["Charge Code"] == "X0000-Operating"
    assert row["Time Sheet Status"] == "Posted"
    assert row["Resource Name"] == "Sanchez, Julian"
    assert row["Time Entry Hours"] == 8.0  # 28800 seconds -> 8 hours


def test_fetch_timesheets_skips_unresolved_contractor(monkeypatch):
    def handler_no_match(request: httpx.Request) -> httpx.Response:
        if request.url.path == clarity_api.RESOURCES_PATH:
            return httpx.Response(200, json={"_results": []})
        raise AssertionError(f"Unexpected request: {request.url.path}")

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler_no_match), **kw),
    )

    df = clarity_api.fetch_timesheets(["Nobody Here"], None, None)
    assert df.empty
    # Empty result must still carry the expected columns, so import_dataframe treats it as a clean
    # 0-row success instead of tripping the "missing required columns" guard (which would misreport a
    # connected-but-no-data API as a fallback and turn the status dot yellow).
    assert list(df.columns) == clarity_api._COLUMNS
