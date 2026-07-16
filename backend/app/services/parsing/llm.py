"""Claude LLM/vision fallback for invoices rules can't handle (scanned PDFs, odd layouts).

Sends the PDF straight to Claude (which can read text PDFs and scanned/image PDFs) and asks for the
structured invoice JSON. Only used when ANTHROPIC_API_KEY is configured; otherwise the orchestrator
skips it.

Token-efficiency design: a SINGLE call returns (a) the extraction, (b) accounting hints (CAPEX/OPEX,
company code, cost center — only if literally printed on the invoice), and (c) a reusable parse
template so the next invoice from this vendor is parsed by pure Python (see templates.py). The LLM
is never called again for a vendor whose template validates.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from app.config import settings
from app.schemas import ParsedInvoice

LLM_MODEL = "claude-opus-4-8"

# Structured-outputs schema for the combined extraction + accounting + template response.
# Constraints: every object needs additionalProperties: false + required (strict mode);
# no numeric/string constraints (unsupported) — normalization happens in Python.
_LINE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "contractor_name": {"type": ["string", "null"]},
        "hours": {"type": ["number", "null"]},
        "rate": {"type": ["number", "null"]},
        "amount": {"type": ["number", "null"]},
        "period_start": {"type": ["string", "null"], "description": "YYYY-MM-DD if printed per-line"},
        "period_end": {"type": ["string", "null"], "description": "YYYY-MM-DD if printed per-line"},
    },
    "required": ["contractor_name", "hours", "rate", "amount", "period_start", "period_end"],
    "additionalProperties": False,
}

_HEADER_FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "strategy": {"type": "string", "enum": ["constant", "regex", "absent"]},
        "value": {"type": ["string", "null"], "description": "for strategy=constant"},
        "pattern": {"type": ["string", "null"], "description": "for strategy=regex; one capture group"},
        "group": {"type": ["integer", "null"], "description": "capture group index, default 1"},
        "labeled": {"type": ["boolean", "null"], "description": "period only: found next to a Period: label"},
    },
    "required": ["strategy", "value", "pattern", "group", "labeled"],
    "additionalProperties": False,
}

_TEMPLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "template_version": {"type": "integer"},
        "fingerprint_regex": {
            "type": "string",
            "description": "regex matching distinctive STATIC text of this vendor (letterhead/name), never invoice-specific values",
        },
        "header": {
            "type": "object",
            "properties": {
                "vendor_name": _HEADER_FIELD_SCHEMA,
                "invoice_number": _HEADER_FIELD_SCHEMA,
                "date_received": _HEADER_FIELD_SCHEMA,
                "payment_period": _HEADER_FIELD_SCHEMA,
                "total_invoice_cost": _HEADER_FIELD_SCHEMA,
            },
            "required": ["vendor_name", "invoice_number", "date_received", "payment_period", "total_invoice_cost"],
            "additionalProperties": False,
        },
        "line_items": {
            "type": "object",
            "properties": {
                "strategy": {"type": "string", "enum": ["line_regex", "table_columns"]},
                "pattern": {
                    "type": ["string", "null"],
                    "description": "line_regex: named groups name/hours/rate/amount (+ optional period_start/period_end)",
                },
                "columns": {
                    "type": ["object", "null"],
                    "description": "table_columns: header keyword per role",
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "hours": {"type": ["string", "null"]},
                        "rate": {"type": ["string", "null"]},
                        "amount": {"type": ["string", "null"]},
                    },
                    "required": ["name", "hours", "rate", "amount"],
                    "additionalProperties": False,
                },
                "skip_row_regex": {"type": ["string", "null"]},
            },
            "required": ["strategy", "pattern", "columns", "skip_row_regex"],
            "additionalProperties": False,
        },
    },
    "required": ["template_version", "fingerprint_regex", "header", "line_items"],
    "additionalProperties": False,
}

_COMBINED_SCHEMA = {
    "type": "object",
    "properties": {
        "extraction": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": ["string", "null"]},
                "invoice_number": {"type": ["string", "null"]},
                "date_received": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
                "payment_period": {"type": ["string", "null"]},
                "total_invoice_cost": {"type": ["number", "null"]},
                "line_items": {"type": "array", "items": _LINE_ITEM_SCHEMA},
            },
            "required": [
                "vendor_name", "invoice_number", "date_received", "payment_period",
                "total_invoice_cost", "line_items",
            ],
            "additionalProperties": False,
        },
        "accounting": {
            "type": "object",
            "properties": {
                "capex_opex": {"type": ["string", "null"], "enum": ["CAPEX", "OPEX", None]},
                "company_code": {"type": ["string", "null"]},
                "cost_center": {"type": ["string", "null"]},
                "project_or_po_reference": {"type": ["string", "null"]},
            },
            "required": ["capex_opex", "company_code", "cost_center", "project_or_po_reference"],
            "additionalProperties": False,
        },
        "template": {"anyOf": [_TEMPLATE_SCHEMA, {"type": "null"}]},
        "template_confidence": {"type": ["string", "null"], "enum": ["high", "low", None]},
    },
    "required": ["extraction", "accounting", "template", "template_confidence"],
    "additionalProperties": False,
}

_PROMPT = """You are extracting data from a contractor invoice PDF for accounts payable.

## 1. extraction
- vendor_name: the supplier/vendor being paid
- invoice_number, date_received (YYYY-MM-DD), payment_period (as written), total_invoice_cost
- line_items: one PER CONTRACTOR/RESOURCE/EMPLOYEE with contractor_name, hours, rate, amount,
  and period_start/period_end (YYYY-MM-DD) if a per-line service period is printed.
Rules: numbers must be plain numbers (15936.00, not "1 5,936.00" or "$15,936"). If the invoice has a
single fixed fee with one person, still produce one line item. If a field is genuinely absent, use
null. Do not invent values.

## 2. accounting
Extract CAPEX/OPEX classification, company code, cost center, and project/PO reference ONLY if they
are literally printed on the invoice. These are advisory hints — downstream systems remain
authoritative. Use null when not printed.

## 3. template (one-and-done learning)
Also emit a reusable parse template so the NEXT invoice from this vendor can be parsed WITHOUT you.
- Regexes are Python `re`, applied with IGNORECASE|MULTILINE to the PDF's literal text layer.
  Mentally test every pattern against the visible text of THIS document.
- fingerprint_regex must match distinctive STATIC vendor text (letterhead/company name), never
  invoice-specific values (numbers, dates, amounts).
- Header patterns: anchor on labels ("Invoice #", "Total Due"), capture the value in group 1.
  Use strategy "constant" for the vendor name if it's stable letterhead; "absent" if a field is
  never printed.
- line_items: prefer strategy "line_regex" with named groups (?P<name>...), (?P<hours>...),
  (?P<rate>...), (?P<amount>...) — optional (?P<period_start>...)/(?P<period_end>...). Use
  "table_columns" (header keyword per role) only for genuinely ruled tables.
- Captured numbers/dates are normalized in Python afterward — capture the raw text, don't worry
  about formats.
- If the layout is not reliably regexable (e.g. this is a scanned image), return template: null and
  template_confidence: null. Set template_confidence to "high" only if you are confident the
  template will parse future invoices from this vendor correctly.
"""


@dataclass
class LLMResult:
    parsed: ParsedInvoice
    accounting: dict | None = None
    template: dict | None = None
    template_confidence: str | None = None


def is_available() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


def extract_with_llm(pdf_path: str) -> LLMResult:
    """Single Claude call: extraction + accounting hints + reusable parse template.

    Raises if no API key is configured or the SDK call fails.
    """
    if not is_available():
        raise RuntimeError("ANTHROPIC_API_KEY not set; LLM parsing unavailable.")

    import anthropic  # imported lazily so the app runs without the key/SDK path

    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    with client.messages.stream(
        model=LLM_MODEL,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": _COMBINED_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ],
    ) as stream:
        msg = stream.get_final_message()

    raw = "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
    data = json.loads(raw)

    extraction = data.get("extraction") or {}
    # Per-line periods ride the existing ParsedLineItem.extra dict (same as rules.py).
    for li in extraction.get("line_items") or []:
        extra = {}
        for k in ("period_start", "period_end"):
            v = li.pop(k, None)
            if v:
                extra[k] = v
        li["extra"] = extra
    parsed = ParsedInvoice.model_validate(extraction)
    if parsed.line_items:
        parsed.contractor_name = parsed.contractor_name or parsed.line_items[0].contractor_name
        parsed.hourly_or_fixed_rate = parsed.line_items[0].rate
        parsed.hours_worked = parsed.line_items[0].hours

    accounting = data.get("accounting")
    if accounting and not any(accounting.values()):
        accounting = None  # nothing printed on the invoice — don't store an all-null blob

    return LLMResult(
        parsed=parsed,
        accounting=accounting,
        template=data.get("template"),
        template_confidence=data.get("template_confidence"),
    )


def parse_with_llm(pdf_path: str) -> ParsedInvoice:
    """Back-compat wrapper: extraction only."""
    return extract_with_llm(pdf_path).parsed
