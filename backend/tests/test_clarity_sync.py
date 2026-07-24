"""Tests for the live-Clarity-API sync path and its CSV/cached-data fallback."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db.base import Base
from app.services import clarity_api, clarity_sync


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'test.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _configure_api(monkeypatch):
    monkeypatch.setattr(settings, "CLARITY_API_URL", "https://clarity.example")
    monkeypatch.setattr(settings, "CLARITY_API_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "CLARITY_API_KEY", "test-key")


def test_unconfigured_marks_status(db: Session):
    # No API key set (default from the autouse fixture) — should skip cleanly, no exception.
    clarity_sync.sync_contractors(db, ["Varun Khetarpal"], date(2026, 1, 1), date(2026, 1, 31))
    status = db.get(models.ClaritySyncStatus, 1)
    assert status is not None
    assert status.source == "unconfigured"
    assert status.last_attempt_at is not None


def test_successful_api_sync_upserts_and_marks_status(db: Session, monkeypatch):
    _configure_api(monkeypatch)
    fake_df = pd.DataFrame(
        [
            {
                "Resource Name": "Khetarpal, Varun",
                "Time Sheet Status": "Posted",
                "Investment ID": "PR00196",
                "Investment Name": "Acima App",
                "Task Name": "Dev",
                "Date Worked": "1/2/26",
                "Time Entry Hours": "20.00",
            }
        ]
    )
    monkeypatch.setattr(clarity_api, "fetch_timesheets", lambda names, start, end: fake_df)

    clarity_sync.sync_contractors(db, ["Varun Khetarpal"], date(2026, 1, 1), date(2026, 1, 31))

    status = db.get(models.ClaritySyncStatus, 1)
    assert status.source == "api"
    assert status.last_success_at is not None
    assert status.last_error is None

    ts = db.scalar(
        select(models.ClarityTimesheet).where(
            models.ClarityTimesheet.contractor_name_normalized == "varun khetarpal"
        )
    )
    assert ts is not None and ts.hours == 20.0


def test_empty_api_result_is_success_not_fallback(db: Session, monkeypatch):
    """A contractor who isn't in Clarity (or has no in-period hours) yields an empty — but
    well-formed — frame. That's the API working and answering, so status must stay 'api' (green
    dot), NOT 'csv_fallback'. Regression for the 'missing required columns' false failure."""
    _configure_api(monkeypatch)
    empty_df = clarity_api.pd.DataFrame(columns=clarity_api._COLUMNS)
    monkeypatch.setattr(clarity_api, "fetch_timesheets", lambda names, start, end: empty_df)

    clarity_sync.sync_contractors(db, ["Ms.SHINIJA B"], date(2026, 1, 1), date(2026, 1, 31))

    status = db.get(models.ClaritySyncStatus, 1)
    assert status.source == "api"
    assert status.last_error is None


def test_api_failure_falls_back_without_touching_cached_data(db: Session, monkeypatch):
    _configure_api(monkeypatch)

    # Seed existing cached data (as if from a prior successful sync or manual CSV import).
    existing = models.ClarityTimesheet(
        contractor_name="Varun Khetarpal",
        contractor_name_normalized="varun khetarpal",
        hours=15.0,
        source_row_hash="preexisting",
    )
    db.add(existing)
    db.commit()

    def _boom(names, start, end):
        raise RuntimeError("Clarity API returned 401 Unauthorized")

    monkeypatch.setattr(clarity_api, "fetch_timesheets", _boom)

    # Must not raise — the invoice pipeline keeps going on cached data.
    clarity_sync.sync_contractors(db, ["Varun Khetarpal"], date(2026, 1, 1), date(2026, 1, 31))

    status = db.get(models.ClaritySyncStatus, 1)
    assert status.source == "csv_fallback"
    assert status.last_error and "401" in status.last_error

    ts = db.scalar(
        select(models.ClarityTimesheet).where(
            models.ClarityTimesheet.contractor_name_normalized == "varun khetarpal"
        )
    )
    assert ts is not None and ts.hours == 15.0  # untouched
