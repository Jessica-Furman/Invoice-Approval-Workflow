"""Tests for learned vendor parse templates (LLM one-and-done learning).

compile/apply/validate are pure (no DB, no LLM). Storage/lookup tests use an in-memory SQLite
session, mirroring the other test modules.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app import models
from app.schemas import ParsedInvoice, ParsedLineItem
from app.services.parsing import templates
from app.services.parsing.templates import (
    TemplateError,
    apply_template,
    compile_template,
    find_template,
    save_template,
    validate_template,
)

SAMPLE_TEXT = (
    "Silverline Consulting LLC\n"
    "123 Main St, Dallas TX\n"
    "Invoice # SLC-2026-041\n"
    "Invoice Date: 06/30/2026\n"
    "Service Period: 06/01/2026 - 06/30/2026\n"
    "Consultant Hours Rate Amount\n"
    "Jane Cooper 160 85.00 13,600.00\n"
    "Marc Diaz 120 95.00 11,400.00\n"
    "Subtotal 25,000.00\n"
    "Total Due $25,000.00\n"
)

SAMPLE_TEMPLATE = {
    "template_version": 1,
    "fingerprint_regex": r"silverline\s+consulting",
    "header": {
        "vendor_name": {"strategy": "constant", "value": "Silverline Consulting LLC"},
        "invoice_number": {"strategy": "regex", "pattern": r"Invoice\s*#\s*([A-Z0-9-]+)", "group": 1},
        "date_received": {"strategy": "regex", "pattern": r"Invoice\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})", "group": 1},
        "payment_period": {
            "strategy": "regex",
            "pattern": r"Service\s*Period:\s*([\d/ -]+\d)",
            "group": 1,
            "labeled": True,
        },
        "total_invoice_cost": {"strategy": "regex", "pattern": r"Total\s*Due\s*\$?([\d,\.]+)", "group": 1},
    },
    "line_items": {
        "strategy": "line_regex",
        "pattern": r"^(?P<name>[A-Z][A-Za-z .'-]+?)\s+(?P<hours>\d+(?:\.\d+)?)\s+(?P<rate>[\d.]+)\s+(?P<amount>[\d,]+\.\d{2})$",
        "skip_row_regex": r"subtotal|total|tax",
    },
}

LLM_EXTRACTION = ParsedInvoice(
    vendor_name="Silverline Consulting LLC",
    invoice_number="SLC-2026-041",
    date_received=date(2026, 6, 30),
    payment_period="06/01/2026 - 06/30/2026",
    total_invoice_cost=25000.0,
    line_items=[
        ParsedLineItem(contractor_name="Jane Cooper", hours=160, rate=85.0, amount=13600.0),
        ParsedLineItem(contractor_name="Marc Diaz", hours=120, rate=95.0, amount=11400.0),
    ],
)


# --- compile ---------------------------------------------------------------
def test_compile_rejects_bad_regex():
    bad = {**SAMPLE_TEMPLATE, "fingerprint_regex": "([unclosed"}
    with pytest.raises(TemplateError):
        compile_template(bad)


def test_compile_rejects_wrong_version():
    with pytest.raises(TemplateError):
        compile_template({**SAMPLE_TEMPLATE, "template_version": 99})


def test_compile_rejects_missing_name_group():
    bad = {
        **SAMPLE_TEMPLATE,
        "line_items": {"strategy": "line_regex", "pattern": r"(?P<hours>\d+)"},
    }
    with pytest.raises(TemplateError):
        compile_template(bad)


def test_compile_rejects_overlong_pattern():
    bad = {**SAMPLE_TEMPLATE, "fingerprint_regex": "a" * 600}
    with pytest.raises(TemplateError):
        compile_template(bad)


# --- apply -------------------------------------------------------------------
def test_apply_template_extracts_everything():
    p = apply_template(SAMPLE_TEMPLATE, SAMPLE_TEXT)
    assert p.vendor_name == "Silverline Consulting LLC"
    assert p.invoice_number == "SLC-2026-041"
    assert p.date_received == date(2026, 6, 30)
    assert p.payment_period_labeled is True
    assert p.total_invoice_cost == 25000.0
    assert [li.contractor_name for li in p.line_items] == ["Jane Cooper", "Marc Diaz"]
    assert p.line_items[0].hours == 160.0
    assert p.line_items[1].amount == 11400.0
    assert p.contractor_name == "Jane Cooper"  # first contractor surfaces to top level


def test_apply_template_table_columns():
    t = {
        "template_version": 1,
        "fingerprint_regex": r"acme\s+staffing",
        "header": {
            "vendor_name": {"strategy": "constant", "value": "Acme Staffing"},
            "invoice_number": {"strategy": "absent"},
            "date_received": {"strategy": "absent"},
            "payment_period": {"strategy": "absent"},
            "total_invoice_cost": {"strategy": "absent"},
        },
        "line_items": {
            "strategy": "table_columns",
            "columns": {"name": "consultant", "hours": "hrs", "rate": "rate", "amount": "amount"},
        },
    }
    tables = [
        [
            ["Consultant", "Hrs", "Rate", "Amount"],
            ["Ada Lovelace", "100", "90.00", "9,000.00"],
            ["Total", "", "", "9,000.00"],
        ]
    ]
    p = apply_template(t, "Acme Staffing invoice", tables)
    assert len(p.line_items) == 1
    assert p.line_items[0].contractor_name == "Ada Lovelace"
    assert p.line_items[0].amount == 9000.0
    assert p.total_invoice_cost == 9000.0  # falls back to line sum


# --- validate ------------------------------------------------------------------
def test_validate_accepts_matching_template():
    ok, reasons = validate_template(SAMPLE_TEMPLATE, SAMPLE_TEXT, [], LLM_EXTRACTION)
    assert ok, reasons


def test_validate_rejects_wrong_extraction():
    wrong = LLM_EXTRACTION.model_copy(deep=True)
    wrong.total_invoice_cost = 99999.0
    wrong.invoice_number = "OTHER-1"
    ok, reasons = validate_template(SAMPLE_TEMPLATE, SAMPLE_TEXT, [], wrong)
    assert not ok
    assert any("total" in r for r in reasons)
    assert any("invoice_number" in r for r in reasons)


def test_validate_rejects_line_count_mismatch():
    wrong = LLM_EXTRACTION.model_copy(deep=True)
    wrong.line_items = wrong.line_items[:1]
    ok, reasons = validate_template(SAMPLE_TEMPLATE, SAMPLE_TEXT, [], wrong)
    assert not ok
    assert any("line count" in r for r in reasons)


# --- storage / lookup ------------------------------------------------------------
@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_save_and_find_template(db):
    save_template(db, "Silverline Consulting LLC", SAMPLE_TEMPLATE, llm_model="claude-opus-4-8")
    db.commit()

    hit = find_template(db, SAMPLE_TEXT)
    assert hit is not None
    assert hit.vendor_key == "silverline consulting llc"
    assert hit.validated is True

    assert find_template(db, "Some Other Vendor Inc invoice text") is None


def test_save_template_upserts_on_vendor_key(db):
    save_template(db, "Silverline Consulting LLC", SAMPLE_TEMPLATE)
    db.commit()
    newer = {**SAMPLE_TEMPLATE, "fingerprint_regex": r"silverline"}
    save_template(db, "Silverline Consulting LLC", newer)
    db.commit()

    rows = db.query(models.VendorParseTemplate).all()
    assert len(rows) == 1
    assert rows[0].fingerprint_regex == "silverline"


def test_find_template_survives_bad_stored_regex(db):
    row = save_template(db, "Broken Vendor", SAMPLE_TEMPLATE)
    row.fingerprint_regex = "([unclosed"
    db.commit()
    assert find_template(db, SAMPLE_TEXT) is None  # must not raise


# --- parser orchestration (rules -> template -> LLM ordering) --------------------
def _low_confidence_rules_result():
    from app.services.parsing import rules

    return rules.RulesResult(
        ParsedInvoice(vendor_name=None, line_items=[]),
        confidence=0.2,
        warnings=[],
        text=SAMPLE_TEXT,
        has_text=True,
        tables=[],
    )


def test_parser_uses_stored_template_before_llm(db, monkeypatch):
    from app.services.parsing import llm, parser, rules

    save_template(db, "Silverline Consulting LLC", SAMPLE_TEMPLATE)
    db.commit()

    monkeypatch.setattr(rules, "parse_with_rules", lambda _: _low_confidence_rules_result())
    monkeypatch.setattr(llm, "is_available", lambda: True)
    monkeypatch.setattr(
        llm, "extract_with_llm",
        lambda _: pytest.fail("LLM must not be called when a stored template succeeds"),
    )

    outcome = parser.parse_invoice("dummy.pdf", db=db)
    assert outcome.method == "template"
    assert outcome.template_id is not None
    assert outcome.parsed.invoice_number == "SLC-2026-041"
    assert len(outcome.parsed.line_items) == 2

    tpl = db.query(models.VendorParseTemplate).one()
    assert tpl.hit_count == 1


def test_parser_learns_template_from_llm(db, monkeypatch):
    from app.services.parsing import llm, parser, rules

    monkeypatch.setattr(rules, "parse_with_rules", lambda _: _low_confidence_rules_result())
    monkeypatch.setattr(llm, "is_available", lambda: True)
    monkeypatch.setattr(
        llm, "extract_with_llm",
        lambda _: llm.LLMResult(
            parsed=LLM_EXTRACTION.model_copy(deep=True),
            accounting={"capex_opex": "OPEX", "company_code": None,
                        "cost_center": None, "project_or_po_reference": None},
            template=SAMPLE_TEMPLATE,
            template_confidence="high",
        ),
    )

    outcome = parser.parse_invoice("dummy.pdf", db=db)
    assert outcome.method == "rules+llm"
    assert outcome.learned_template == SAMPLE_TEMPLATE  # validated against SAMPLE_TEXT
    assert outcome.llm_accounting["capex_opex"] == "OPEX"


def test_parser_rejects_template_that_fails_validation(db, monkeypatch):
    from app.services.parsing import llm, parser, rules

    wrong_extraction = LLM_EXTRACTION.model_copy(deep=True)
    wrong_extraction.total_invoice_cost = 1.0  # template output won't reproduce this

    monkeypatch.setattr(rules, "parse_with_rules", lambda _: _low_confidence_rules_result())
    monkeypatch.setattr(llm, "is_available", lambda: True)
    monkeypatch.setattr(
        llm, "extract_with_llm",
        lambda _: llm.LLMResult(
            parsed=wrong_extraction, template=SAMPLE_TEMPLATE, template_confidence="high",
        ),
    )

    outcome = parser.parse_invoice("dummy.pdf", db=db)
    assert outcome.learned_template is None
    assert any("failed validation" in w for w in outcome.warnings)


def test_parser_skips_templates_without_db(monkeypatch):
    from app.services.parsing import llm, parser, rules

    monkeypatch.setattr(rules, "parse_with_rules", lambda _: _low_confidence_rules_result())
    monkeypatch.setattr(llm, "is_available", lambda: False)

    outcome = parser.parse_invoice("dummy.pdf")  # no db, no key — plain rules result
    assert outcome.method == "rules"
