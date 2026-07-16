"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import clarity, invoices, other_invoices, reports
from app.config import settings
from app.db.base import init_db

app = FastAPI(title="InVoicee API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Browsers hide Content-Disposition from cross-origin JS unless it's explicitly exposed — the
    # frontend reads it to name CSV/Excel downloads (else it falls back to a generic name).
    expose_headers=["Content-Disposition"],
)


@app.on_event("startup")
def _startup() -> None:
    # Ensure tables exist on boot (idempotent). Seeding is a separate explicit step.
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(invoices.router)
app.include_router(clarity.router)
app.include_router(other_invoices.router)
app.include_router(reports.router)
