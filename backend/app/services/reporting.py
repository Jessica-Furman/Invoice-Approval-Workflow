"""Executive invoice report: Python-side aggregation + optional Claude narrative.

Token-efficiency design: ALL numbers are computed here in SQL/Python — the LLM (triggered only by
the dashboard's "Create Report" button) receives just the compact aggregate JSON and writes the
executive narrative. Raw invoices/line items are never sent to the API.

Classification sources (same authorities as the Coupa CSV):
- CAPEX/OPEX + company (RAC/ACIMA): matched Clarity timesheet/project via coupa helpers.
- Unmatched contractor lines: fall back to the LLM's "vendor-stated" hint (raw_extraction).
- Other invoices: offset GL account mapped back through CAPEX_OPEX_CODE; cost center from the
  copy tracker / budget sheet already stored on the invoice.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models
from app.config import settings
from app.services.coupa import (
    CAPEX_OPEX_CODE,
    COMPANY_CODE,
    COST_CENTER,
    _capex_opex_for,
    _clarity_project_breakdown,
    _company_for_project,
    _norm_capex,
)

LLM_MODEL = "claude-opus-4-8"
TOP_VENDORS = 15
TOP_PROJECTS = 5

_GL_TO_CAPEX = {code: label for label, code in CAPEX_OPEX_CODE.items()}  # 246010 -> CAPEX, ...


def _line_weight(li: models.InvoiceLineItem) -> float:
    if li.amount is not None:
        return li.amount
    if li.hours is not None and li.rate is not None:
        return li.hours * li.rate
    return 0.0


def _r(x: float) -> float:
    return round(x, 2)


def compute_aggregates(db: Session, start: date | None = None, end: date | None = None) -> dict:
    """Aggregate all processed invoices (contractor + other, archived included) into report buckets."""
    q = select(models.Invoice).options(
        selectinload(models.Invoice.line_items).selectinload(models.InvoiceLineItem.matched_clarity)
    )
    if start:
        q = q.where(models.Invoice.date_received >= start)
    if end:
        q = q.where(models.Invoice.date_received <= end)
    invoices = db.execute(q).scalars().all()

    projects = {
        p.project_id: p
        for p in db.execute(select(models.ClarityProject)).scalars().all()
        if p.project_id
    }

    contractor = [i for i in invoices if i.invoice_type == models.INVOICE_TYPE_CONTRACTOR]
    other = [i for i in invoices if i.invoice_type == models.INVOICE_TYPE_OTHER]

    contractor_spend = sum(i.total_invoice_cost or 0 for i in contractor)
    other_spend = sum(i.total_invoice_cost or 0 for i in other)

    status_counts: dict[str, int] = defaultdict(int)
    method_counts: dict[str, int] = defaultdict(int)
    for i in invoices:
        status_counts[i.status] += 1
        method = (i.raw_extraction or {}).get("method")
        if method:
            method_counts[method] += 1

    confidences = [i.parse_confidence for i in contractor if i.parse_confidence is not None]

    # --- CAPEX/OPEX + company + cost center (contractor lines) -------------------------------
    capex_opex: dict[str, float] = defaultdict(float)
    by_company: dict[str, float] = defaultdict(float)
    by_cost_center: dict[str, float] = defaultdict(float)
    # Project spend: a contractor's line amount split across Clarity investments by that
    # investment's share of the contractor's counted hours in the line's period. "Unresolved"
    # catches lines with no Clarity match (or zero counted in-period hours).
    by_project: dict[str, float] = defaultdict(float)

    for inv in contractor:
        hint = _norm_capex(((inv.raw_extraction or {}).get("llm_accounting") or {}).get("capex_opex"))
        for li in inv.line_items:
            w = _line_weight(li)
            if w == 0:
                continue
            ts = li.matched_clarity
            project = projects.get(ts.project_id) if ts and ts.project_id else None
            cls = _capex_opex_for(li, project)
            if cls:
                capex_opex[cls] += w
            elif hint:
                capex_opex[f"vendor_stated_{hint.lower()}"] += w
            else:
                capex_opex["unclassified"] += w

            company = _company_for_project(ts.project_id, ts.investment_name) if ts else None
            by_company[company or "unresolved"] += w
            cc = COST_CENTER.get(company) if company else None
            by_cost_center[cc or "unresolved"] += w

            proj_hours = _clarity_project_breakdown(li, inv, db)
            total_proj_hours = sum(proj_hours.values()) if proj_hours else 0
            if proj_hours and total_proj_hours:
                for label, hours in proj_hours.items():
                    by_project[label] += w * (hours / total_proj_hours)
            else:
                by_project["Unresolved"] += w

    # --- Other invoices: GL account -> CAPEX/OPEX, stored cost center -------------------------
    for inv in other:
        w = inv.total_invoice_cost or 0
        if w == 0:
            continue
        raw = inv.raw_extraction or {}
        cls = _GL_TO_CAPEX.get(str(raw.get("offset_gl_account") or "").strip())
        capex_opex[cls or "unclassified"] += w
        cc = (raw.get("cost_center") or "").strip() or "unresolved"
        by_cost_center[cc] += w
        # "Other" invoices (hardware/software) have no Clarity project link today.
        by_project["Unresolved"] += w

    # --- Vendors (both types, top N + Other) ---------------------------------------------------
    vendor_rows: dict[str, dict] = {}
    for inv in invoices:
        name = inv.vendor_name or "Unknown vendor"
        row = vendor_rows.setdefault(name, {"vendor": name, "spend": 0.0, "invoice_count": 0,
                                            "type": inv.invoice_type})
        row["spend"] += inv.total_invoice_cost or 0
        row["invoice_count"] += 1
    ranked = sorted(vendor_rows.values(), key=lambda r: r["spend"], reverse=True)
    top = ranked[:TOP_VENDORS]
    rest = ranked[TOP_VENDORS:]
    if rest:
        top.append({
            "vendor": "Other",
            "spend": sum(r["spend"] for r in rest),
            "invoice_count": sum(r["invoice_count"] for r in rest),
            "type": "mixed",
        })
    by_vendor = [{**r, "spend": _r(r["spend"])} for r in top]

    # --- Projects (top N + Other, "Unresolved" kept separate) ----------------------------------
    named_projects = sorted(
        ((name, amt) for name, amt in by_project.items() if name != "Unresolved" and amt > 0),
        key=lambda kv: kv[1], reverse=True,
    )
    top_projects = [{"project": name, "spend": _r(amt)} for name, amt in named_projects[:TOP_PROJECTS]]
    rest_projects = named_projects[TOP_PROJECTS:]
    if rest_projects:
        top_projects.append({"project": "Other", "spend": _r(sum(amt for _, amt in rest_projects))})
    unresolved_project_spend = by_project.get("Unresolved", 0.0)
    if unresolved_project_spend > 0:
        top_projects.append({"project": "Unresolved", "spend": _r(unresolved_project_spend)})

    # --- Monthly trend --------------------------------------------------------------------------
    months: dict[str, dict] = defaultdict(lambda: {"contractor_spend": 0.0, "other_spend": 0.0,
                                                   "invoice_count": 0})
    for inv in invoices:
        if not inv.date_received:
            continue
        key = inv.date_received.strftime("%Y-%m")
        bucket = months[key]
        if inv.invoice_type == models.INVOICE_TYPE_OTHER:
            bucket["other_spend"] += inv.total_invoice_cost or 0
        else:
            bucket["contractor_spend"] += inv.total_invoice_cost or 0
        bucket["invoice_count"] += 1
    monthly_trend = [
        {"month": m, "contractor_spend": _r(v["contractor_spend"]),
         "other_spend": _r(v["other_spend"]), "invoice_count": v["invoice_count"]}
        for m, v in sorted(months.items())
    ]

    classified_total = sum(capex_opex.values())
    return {
        "period": {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "generated_from_invoices": len(invoices),
        },
        "totals": {
            "combined_spend": _r(contractor_spend + other_spend),
            "contractor_spend": _r(contractor_spend),
            "other_spend": _r(other_spend),
            "invoice_count": len(invoices),
            "contractor_invoice_count": len(contractor),
            "other_invoice_count": len(other),
            "status_counts": dict(status_counts),
            "parse_method_counts": dict(method_counts),
            "avg_parse_confidence": _r(sum(confidences) / len(confidences)) if confidences else None,
        },
        "capex_opex": {
            "amounts": {k: _r(v) for k, v in sorted(capex_opex.items())},
            "pct": {
                k: _r(100 * v / classified_total) for k, v in sorted(capex_opex.items())
            } if classified_total else {},
        },
        "by_company": {
            (k or "unresolved"): {
                "spend": _r(v),
                "company_code": COMPANY_CODE.get(k),
                "cost_center": COST_CENTER.get(k),
            }
            for k, v in sorted(by_company.items(), key=lambda kv: kv[1], reverse=True)
        },
        "by_cost_center": {k: _r(v) for k, v in sorted(by_cost_center.items(),
                                                       key=lambda kv: kv[1], reverse=True)},
        "by_vendor": by_vendor,
        "by_project": top_projects,
        "monthly_trend": monthly_trend,
    }


_NARRATIVE_PROMPT = """You are writing an executive spend report for the finance leadership of
Upbound Group (companies: Rent-A-Center "RAC" company code 5, Acima company code 67), covering
processed contractor and vendor invoices.

The JSON below contains every figure, pre-aggregated. Write a Markdown report with EXACTLY these
sections:

## Executive Summary
3-4 sentences: total spend, invoice volume, headline composition.

## Key Insights
4-6 bullets, each citing specific figures (top vendors, top projects by spend, concentration,
trend direction, CAPEX vs OPEX balance, match rate).

## Spend Composition
Short commentary on CAPEX vs OPEX split, the RAC vs Acima company split (cost centers H0003 /
AC000), and which project(s) drove the most spend this period.

## Risks & Flags
Flagged/unmatched invoices, unclassified spend, low parse confidence — anything needing attention.

## Recommendations
2-4 concrete, actionable bullets.

Rules: use ONLY the figures provided — never invent or extrapolate numbers. Format money like
$1,234,567.89 (or $1.2M where a round figure reads better). "vendor_stated_*" buckets are
CAPEX/OPEX classifications read off the invoice itself rather than from Clarity — treat them as
lower-confidence. In `by_project`, "Other" is the sum of projects outside the top 5 and
"Unresolved" is spend that couldn't be attributed to a specific Clarity project — both mean the
data pipeline could not classify that spend, same as "unclassified"/"unresolved" elsewhere.

Aggregates:
"""


def generate_narrative(aggregates: dict) -> str | None:
    """One Claude call turning the aggregate JSON into an executive narrative. None without a key."""
    if not settings.ANTHROPIC_API_KEY:
        return None

    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        messages=[{
            "role": "user",
            "content": _NARRATIVE_PROMPT + json.dumps(aggregates, separators=(",", ":")),
        }],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip() or None
