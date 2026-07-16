"""Tests for the executive report aggregation (+ report API endpoint, no LLM)."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.api.reports import ReportRequest, create_report
from app.db.base import Base
from app.services.reporting import compute_aggregates, generate_narrative
from app.utils.names import normalize_name


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path/'r.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _seed(db: Session) -> None:
    # Company resolution falls back to the investment-name regex (\brac / \bacima) since the
    # Company_by_Project.csv mapping won't contain these synthetic project ids.
    ts_rac = models.ClarityTimesheet(
        contractor_name="Jane Doe", contractor_name_normalized=normalize_name("Jane Doe"),
        hours=10, date_worked=date(2026, 5, 5), is_posted=True, is_time_off=False,
        project_id="PX-1", investment_name="RAC Portal", capex_opex="CAPEX",
        source_row_hash="ts-rac",
    )
    ts_acima = models.ClarityTimesheet(
        contractor_name="Marc Diaz", contractor_name_normalized=normalize_name("Marc Diaz"),
        hours=5, date_worked=date(2026, 5, 6), is_posted=True, is_time_off=False,
        project_id="PX-2", investment_name="Acima Mobile App", capex_opex="OPEX",
        source_row_hash="ts-acima",
    )
    db.add_all([ts_rac, ts_acima])
    db.flush()

    # Matched contractor invoice: one RAC/CAPEX line + one ACIMA/OPEX line.
    db.add(models.Invoice(
        vendor_name="AVASOFT", invoice_number="A-1", status=models.STATUS_MATCHED,
        date_received=date(2026, 5, 15), total_invoice_cost=1500.0, parse_confidence=0.9,
        raw_extraction={"method": "rules"},
        line_items=[
            models.InvoiceLineItem(contractor_name="Jane Doe", amount=1000.0,
                                   matched_clarity_id=ts_rac.id),
            models.InvoiceLineItem(contractor_name="Marc Diaz", amount=500.0,
                                   matched_clarity_id=ts_acima.id),
        ],
    ))

    # Unmatched contractor invoice with a vendor-stated (LLM) OPEX hint.
    db.add(models.Invoice(
        vendor_name="Silverline", invoice_number="B-1", status=models.STATUS_FLAGGED,
        date_received=date(2026, 6, 10), total_invoice_cost=200.0, parse_confidence=0.7,
        raw_extraction={"method": "rules+llm", "llm_accounting": {"capex_opex": "OPEX"}},
        line_items=[models.InvoiceLineItem(contractor_name="Ada Lovelace", amount=200.0)],
    ))

    # "Other" invoice classified via its offset GL account (246010 -> CAPEX).
    db.add(models.Invoice(
        vendor_name="Adobe", invoice_number="C-1", status=models.STATUS_ALL_DATA_FOUND,
        invoice_type=models.INVOICE_TYPE_OTHER,
        date_received=date(2026, 6, 20), total_invoice_cost=300.0,
        raw_extraction={"method": "rules", "offset_gl_account": "246010", "cost_center": "H0003"},
    ))
    db.commit()


def test_totals_and_status_counts(db: Session):
    _seed(db)
    agg = compute_aggregates(db)
    t = agg["totals"]
    assert t["combined_spend"] == 2000.0
    assert t["contractor_spend"] == 1700.0
    assert t["other_spend"] == 300.0
    assert t["invoice_count"] == 3
    assert t["status_counts"][models.STATUS_MATCHED] == 1
    assert t["status_counts"][models.STATUS_FLAGGED] == 1
    assert t["parse_method_counts"] == {"rules": 2, "rules+llm": 1}
    assert t["avg_parse_confidence"] == 0.8


def test_capex_opex_buckets(db: Session):
    _seed(db)
    amounts = compute_aggregates(db)["capex_opex"]["amounts"]
    # CAPEX = RAC line (1000, Clarity) + other invoice via GL 246010 (300).
    assert amounts["CAPEX"] == 1300.0
    assert amounts["OPEX"] == 500.0
    # The unmatched Silverline line falls back to the invoice's LLM-read hint.
    assert amounts["vendor_stated_opex"] == 200.0
    assert "unclassified" not in amounts


def test_company_and_cost_center_buckets(db: Session):
    _seed(db)
    agg = compute_aggregates(db)
    assert agg["by_company"]["RAC"]["spend"] == 1000.0
    assert agg["by_company"]["RAC"]["company_code"] == "5"
    assert agg["by_company"]["ACIMA"]["spend"] == 500.0
    assert agg["by_company"]["unresolved"]["spend"] == 200.0
    # H0003 = RAC contractor line (1000) + other invoice stored cost center (300).
    assert agg["by_cost_center"]["H0003"] == 1300.0
    assert agg["by_cost_center"]["AC000"] == 500.0


def test_vendor_ranking_and_trend(db: Session):
    _seed(db)
    agg = compute_aggregates(db)
    assert agg["by_vendor"][0]["vendor"] == "AVASOFT"
    assert agg["by_vendor"][0]["spend"] == 1500.0

    trend = {m["month"]: m for m in agg["monthly_trend"]}
    assert trend["2026-05"]["contractor_spend"] == 1500.0
    assert trend["2026-06"]["contractor_spend"] == 200.0
    assert trend["2026-06"]["other_spend"] == 300.0
    assert trend["2026-06"]["invoice_count"] == 2


def test_date_range_filter(db: Session):
    _seed(db)
    agg = compute_aggregates(db, start=date(2026, 6, 1), end=date(2026, 6, 30))
    assert agg["totals"]["invoice_count"] == 2
    assert agg["totals"]["combined_spend"] == 500.0
    assert agg["period"]["start"] == "2026-06-01"


def test_narrative_none_without_key():
    assert generate_narrative({"totals": {}}) is None  # key blanked by conftest


def test_html_report_is_self_contained(db: Session):
    from app.api.reports import create_report_html
    from app.services.report_html import report_html_bytes

    _seed(db)
    resp = create_report_html(ReportRequest(), db)
    page = resp.body.decode("utf-8")

    assert "<svg" in page                                # charts are inline SVG
    assert "AVASOFT" in page                             # vendor bars present
    assert "ANTHROPIC_API_KEY not configured" in page    # narrative note (no key in tests)
    # Self-contained: no external requests — no remote src/href, no CDN script/link tags.
    assert not re.search(r'(src|href)\s*=\s*"https?://', page)
    assert "<script" not in page and "<link" not in page
    assert "attachment" in resp.headers["content-disposition"]


def test_html_report_renders_markdown_narrative(db: Session):
    from app.services.report_html import report_html_bytes

    _seed(db)
    md = "## Executive Summary\nSpend was **$2,000.00**.\n- CAPEX leads\n- OPEX steady"
    page = report_html_bytes(compute_aggregates(db), md).decode("utf-8")
    assert "<h2>Executive Summary</h2>" in page
    assert "<strong>$2,000.00</strong>" in page
    assert "<li>CAPEX leads</li>" in page


def test_report_endpoint_returns_aggregates_and_audits(db: Session):
    _seed(db)
    resp = create_report(ReportRequest(), db)
    assert resp.narrative is None
    assert resp.llm_available is False
    assert resp.aggregates["totals"]["invoice_count"] == 3

    audit = db.query(models.AuditLog).filter_by(event="report_generated").one()
    assert audit.detail["invoices"] == 3
    assert audit.detail["llm"] is False
