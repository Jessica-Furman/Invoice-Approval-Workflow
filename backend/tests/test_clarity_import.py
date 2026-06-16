"""Tests for the Clarity import service (M2)."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import models
from app.db.base import Base
from app.services.clarity_import import import_timesheets
from app.utils.names import clarity_to_first_last, normalize_name


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'test.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _write_csv(tmp_path: Path) -> str:
    # Varun: two entries SAME date+investment (sum to 30), one on another investment, plus a Time Off
    # entry that must be flagged separately. Oscar on one project. One blank-Investment row.
    content = textwrap.dedent(
        """\
        Resource Name,Resource Manager,Time Sheet Status,Period Start Date,Period Finish Date,Investment ID,Investment Name,Investment Manager,Charge Code,Task Name,Date Worked,Time Entry Hours
        "Khetarpal, Varun","Loiseau, Chad",Posted,12/28/25,1/3/26,PR00196,Acima App,"Vippala, Lokitha",U0000-Upbound Capital,Dev,1/2/26,20.00
        "Khetarpal, Varun","Loiseau, Chad",Posted,12/28/25,1/3/26,PR00196,Acima App,"Vippala, Lokitha",U0000-Upbound Capital,Dev,1/2/26,10.00
        "Khetarpal, Varun","Loiseau, Chad",Posted,12/28/25,1/3/26,PR00041,Digital Infra,"Sabadie, Erik",X0000-Operating,Support,1/2/26,5.00
        "Khetarpal, Varun","Loiseau, Chad",Posted,12/28/25,1/3/26,PR00196,Acima App,"Vippala, Lokitha",U0000-Upbound Capital,Time Off,1/5/26,8.00
        "Khetarpal, Varun","Loiseau, Chad",Posted,12/28/25,1/3/26,PR00196,Acima App,"Vippala, Lokitha",U0000-Upbound Capital,PTO,1/6/26,7.00
        "Khetarpal, Varun","Loiseau, Chad",Returned,12/28/25,1/3/26,PR00196,Acima App,"Vippala, Lokitha",U0000-Upbound Capital,Dev,1/7/26,4.00
        "Trelles, Oscar","Sabadie, Erik",Posted,2/15/26,2/21/26,PR00041,Digital Infra,"Sabadie, Erik",X0000-Operating,Support,2/20/26,17.00
        "No Project, Person","Mgr, A",Posted,2/15/26,2/21/26,,,,,Misc,2/20/26,3.00
        """
    )
    p = tmp_path / "clarity.csv"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_name_normalization():
    assert clarity_to_first_last("Khetarpal, Varun") == "Varun Khetarpal"
    assert normalize_name("Khetarpal, Varun") == "varun khetarpal"
    assert normalize_name("Varun Khetarpal") == "varun khetarpal"


def test_charge_code_classification():
    from app.services.clarity_import import classify_charge_code

    assert classify_charge_code("U0000-Upbound Capital") == "CAPEX"
    assert classify_charge_code("X0000-Operating") == "OPEX"
    assert classify_charge_code("Z9999-Something Else") is None
    assert classify_charge_code(None) is None


def test_aggregates_and_is_idempotent(db: Session, tmp_path: Path):
    csv = _write_csv(tmp_path)

    r1 = import_timesheets(db, csv)
    assert r1.source_rows == 8
    # Date-level groups (resource, date, investment, time-off, posted):
    #  (Varun,1/2,PR00196,work,posted)[30], (Varun,1/2,PR00041,work,posted)[5],
    #  (Varun,1/5,PR00196,Time Off,posted)[8], (Varun,1/6,PR00196,PTO,posted)[7],
    #  (Varun,1/7,PR00196,work,NOT posted)[4], (Oscar,2/20,PR00041,work,posted)[17], (blank)[3] = 7
    assert r1.aggregated_rows == 7
    assert r1.timesheets_created == 7

    # Billable posted, non-time-off row for PR00196 (the two same date+investment entries summed).
    varun = db.scalar(
        select(models.ClarityTimesheet).where(
            models.ClarityTimesheet.contractor_name_normalized == "varun khetarpal",
            models.ClarityTimesheet.project_id == "PR00196",
            models.ClarityTimesheet.is_time_off.is_(False),
            models.ClarityTimesheet.is_posted.is_(True),
        )
    )
    assert varun is not None and varun.hours == 30.0
    assert varun.date_worked.isoformat() == "2026-01-02"
    assert varun.capex_opex == "CAPEX"

    # Both "Time Off" and "PTO" are flagged as time-off.
    timeoff_hours = {
        t.hours
        for t in db.scalars(
            select(models.ClarityTimesheet).where(models.ClarityTimesheet.is_time_off.is_(True))
        ).all()
    }
    assert timeoff_hours == {8.0, 7.0}

    # The "Returned" timesheet is not posted.
    returned = db.scalar(
        select(models.ClarityTimesheet).where(models.ClarityTimesheet.is_posted.is_(False))
    )
    assert returned is not None and returned.hours == 4.0 and returned.time_sheet_status == "Returned"

    assert db.scalar(select(func.count()).select_from(models.ClarityProject)) == 2

    # Second import: nothing new.
    r2 = import_timesheets(db, csv)
    assert r2.timesheets_created == 0
    assert r2.timesheets_updated == 7
    assert r2.projects_created == 0
    assert db.scalar(select(func.count()).select_from(models.ClarityTimesheet)) == 7
