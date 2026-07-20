"""Shared test config.

Force the Anthropic key off for the entire test session: tests must never hit the real API (or
spend tokens), even after the user puts a real ANTHROPIC_API_KEY in the repo-root .env.
Tests that exercise LLM paths monkeypatch `llm.extract_with_llm` instead.
"""
from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _no_llm_key(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")


@pytest.fixture(autouse=True)
def _no_clarity_api(monkeypatch):
    """Force the live Clarity API off for every test — no test should ever attempt a real call.
    Tests exercising the sync path monkeypatch `clarity_api.fetch_timesheets` instead."""
    monkeypatch.setattr(settings, "CLARITY_API_URL", "")
    monkeypatch.setattr(settings, "CLARITY_API_CLIENT_ID", "")
    monkeypatch.setattr(settings, "CLARITY_API_KEY", "")
