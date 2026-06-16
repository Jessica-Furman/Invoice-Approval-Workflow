"""Clarity import + read API (M2)."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db.base import get_db
from app.schemas import ClarityProjectOut, ClarityTimesheetOut
from app.services.clarity_import import import_timesheets

router = APIRouter(prefix="/api/clarity", tags=["clarity"])


@router.post("/import")
async def import_clarity(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    """Upload a Clarity TimeEntry CSV/Excel export, save it, and import it idempotently."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    dest_dir = Path(settings.CLARITY_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        result = import_timesheets(db, str(dest))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"file": file.filename, **result.as_dict()}


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    return {
        "timesheets": db.scalar(select(func.count()).select_from(models.ClarityTimesheet)) or 0,
        "projects": db.scalar(select(func.count()).select_from(models.ClarityProject)) or 0,
        "contractors": db.scalar(
            select(func.count(func.distinct(models.ClarityTimesheet.contractor_name_normalized)))
        )
        or 0,
    }


@router.get("/timesheets", response_model=list[ClarityTimesheetOut])
def list_timesheets(
    search: str | None = None, limit: int = 50, db: Session = Depends(get_db)
) -> list[models.ClarityTimesheet]:
    q = select(models.ClarityTimesheet).order_by(models.ClarityTimesheet.contractor_name)
    if search:
        q = q.where(models.ClarityTimesheet.contractor_name_normalized.contains(search.lower()))
    return list(db.scalars(q.limit(min(limit, 500))).all())


@router.get("/projects", response_model=list[ClarityProjectOut])
def list_projects(limit: int = 50, db: Session = Depends(get_db)) -> list[models.ClarityProject]:
    return list(
        db.scalars(
            select(models.ClarityProject).order_by(models.ClarityProject.project_id).limit(min(limit, 500))
        ).all()
    )
