"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from pathlib import Path

from pydantic import model_validator
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

    @model_validator(mode="after")
    def _anchor_relative_paths(self) -> "Settings":
        """Anchor relative storage/inbox/clarity paths (and a relative sqlite DB) to the repo root.

        These paths may be overridden in .env with values relative to the repo (e.g. "./data/storage").
        A relative value resolves against the *current working directory*, so the app would read/write
        different folders depending on whether the server was launched from the repo root or from
        backend/. That split the invoice PDFs across <repo>/data/storage and <repo>/backend/data/storage
        while the single (absolute-path) SQLite DB kept one set of records — producing "PDF file missing
        from storage" for invoices uploaded from the other directory. Anchoring to REPO_ROOT makes every
        path resolve to the same location no matter where the process starts.
        """
        for field in (
            "INBOX_CONTRACTOR_DIR",
            "INBOX_MATCHED_DIR",
            "INBOX_FLAGGED_DIR",
            "STORAGE_DIR",
            "CLARITY_DIR",
        ):
            value = getattr(self, field)
            if value and not Path(value).is_absolute():
                setattr(self, field, str((REPO_ROOT / value).resolve()))

        prefix = "sqlite:///"
        if self.DATABASE_URL.startswith(prefix):
            raw = self.DATABASE_URL[len(prefix):]
            if raw and not raw.startswith("/") and not Path(raw).is_absolute():
                self.DATABASE_URL = prefix + (REPO_ROOT / raw).resolve().as_posix()
        return self


settings = Settings()
