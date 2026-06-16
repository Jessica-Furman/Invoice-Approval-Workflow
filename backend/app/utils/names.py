"""Shared name normalization helpers.

Clarity exports names as "Last, First" (e.g. "Khetarpal, Varun"); invoices use "First Last".
We normalize both into a canonical key so they can be matched (User Stories 6, 7).
"""
from __future__ import annotations

import re


def clarity_to_first_last(name: str | None) -> str | None:
    """'Khetarpal, Varun' -> 'Varun Khetarpal'. Pass-through if no comma."""
    if not name:
        return None
    name = name.strip()
    if "," in name:
        last, first = name.split(",", 1)
        return f"{first.strip()} {last.strip()}".strip()
    return name


def normalize_name(name: str | None) -> str | None:
    """Canonical matching key: handle 'Last, First', lowercase, strip punctuation, collapse spaces."""
    if not name:
        return None
    name = clarity_to_first_last(name)
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n or None
