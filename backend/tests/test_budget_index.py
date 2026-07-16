"""Tests for Budget_ID's.xlsx routing (Other invoices): vendor-first, then description -> Product (F)."""
from __future__ import annotations

import app.services.budget_index as bi
from app.services.budget_index import BudgetRow, budget_route


def _rows() -> list[BudgetRow]:
    # A few Salesforce budget lines (all DT600) + one Slack line, mirroring the real sheet's shape.
    return [
        BudgetRow("salesforce inc", "salesforce b2b", "BUD-00046", "DT600", "Farooq Buvvaji", "131120", "RAC-250849"),
        BudgetRow("salesforce inc", "salesforce commerce cloud", "BUD-01048", "DT600", "Farooq Buvvaji", "131120", "RAC-250849"),
        BudgetRow("salesforce inc", "mulesoft", "BUD-00109", "DT600", "Pranav Sharma", "131120", "RAC-250849"),
        BudgetRow("slack", "slack", "BUD-00486", "DT600", "Elishia Williams", "679030", "RAC-99999"),
    ]


def test_budget_route_matches_vendor_then_description(monkeypatch):
    monkeypatch.setattr(bi, "_budget_rows", _rows)
    r = budget_route("Salesforce, Inc", ["Additional Orders - B2B Commerce", "B2B Commerce Platform"])
    assert r["budget_id"] == "BUD-00046"       # 'B2B' beats 'Commerce Cloud' / 'MULESOFT'
    assert r["cost_center"] == "DT600"
    assert r["approver"] == "Farooq Buvvaji"
    assert r["offset_gl_account"] == "131120"
    assert r["supplier_number"] == "RAC-250849"


def test_budget_route_consensus_when_description_is_ambiguous(monkeypatch):
    monkeypatch.setattr(bi, "_budget_rows", _rows)
    # A description with no product signal -> no specific budget id, but the vendor's rows unanimously
    # agree on cost center / GL / supplier number, so those still resolve (the tracker fallback use).
    r = budget_route("Salesforce, Inc", ["monthly subscription services"])
    assert r["cost_center"] == "DT600"          # all Salesforce rows agree
    assert r["offset_gl_account"] == "131120"
    assert r["supplier_number"] == "RAC-250849"
    assert r["approver"] is None                # approvers differ (Farooq vs Pranav) -> ambiguous


def test_budget_route_unknown_vendor_is_all_none(monkeypatch):
    monkeypatch.setattr(bi, "_budget_rows", _rows)
    assert budget_route("Totally Unknown Vendor", ["stuff"]) == {
        "budget_id": None, "cost_center": None, "approver": None,
        "offset_gl_account": None, "supplier_number": None,
    }


def test_budget_route_no_vendor_returns_none(monkeypatch):
    monkeypatch.setattr(bi, "_budget_rows", _rows)
    assert budget_route(None, ["x"])["cost_center"] is None
