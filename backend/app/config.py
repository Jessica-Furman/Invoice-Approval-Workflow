"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = two levels up from this file (backend/app/config.py -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database: SQLite by default (no install needed). Postgres-ready via DATABASE_URL.
    DATABASE_URL: str = f"sqlite:///{(REPO_ROOT / 'data' / 'invoicee.sqlite3').as_posix()}"

    # Invoice parsing (M3)
    ANTHROPIC_API_KEY: str = ""

    # Clarity API (live timesheet sync) — CSV import remains the fallback when unset/unreachable.
    # Key-based auth: CLARITY_API_CLIENT_ID goes in the x-api-ppm-client header, CLARITY_API_KEY as
    # "Authorization: Bearer <key>" (no login/session step needed).
    CLARITY_API_URL: str = ""
    CLARITY_API_CLIENT_ID: str = ""
    CLARITY_API_KEY: str = ""
    CLARITY_API_TIMEOUT_SECONDS: float = 8.0

    # Local mock paths
    INBOX_CONTRACTOR_DIR: str = str(REPO_ROOT / "data" / "inbox" / "contractor_invoices")
    INBOX_MATCHED_DIR: str = str(REPO_ROOT / "data" / "inbox" / "matched")
    INBOX_FLAGGED_DIR: str = str(REPO_ROOT / "data" / "inbox" / "flagged")
    STORAGE_DIR: str = str(REPO_ROOT / "data" / "storage")
    CLARITY_DIR: str = str(REPO_ROOT / "data" / "clarity")

    # CORS — Vite dev server
    FRONTEND_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
