"""Hybrid parse orchestrator: rules first, Claude fallback when needed and available."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import ParsedInvoice
from app.services.parsing import llm, rules

# Below this rules-confidence, try the LLM (if a key is configured).
CONFIDENCE_THRESHOLD = 0.8
REQUIRED_FIELDS = ("vendor_name", "invoice_number", "date_received", "total_invoice_cost")


@dataclass
class ParseOutcome:
    parsed: ParsedInvoice
    confidence: float
    method: str  # "rules" | "llm" | "rules+llm"
    has_text: bool
    warnings: list[str] = field(default_factory=list)

    def missing_required(self) -> list[str]:
        return [f for f in REQUIRED_FIELDS if not getattr(self.parsed, f)]


def _needs_llm(r: rules.RulesResult) -> bool:
    if not r.has_text:
        return True
    if r.confidence < CONFIDENCE_THRESHOLD:
        return True
    if any(not getattr(r.parsed, f) for f in REQUIRED_FIELDS):
        return True
    return not r.parsed.line_items


def _merge(base: ParsedInvoice, fallback: ParsedInvoice) -> ParsedInvoice:
    """Fill gaps in `base` (rules) from `fallback` (LLM); take LLM line items if rules found none."""
    merged = base.model_copy(deep=True)
    for f in ("vendor_name", "invoice_number", "date_received", "payment_period",
              "hourly_or_fixed_rate", "hours_worked", "total_invoice_cost", "contractor_name"):
        if not getattr(merged, f) and getattr(fallback, f):
            setattr(merged, f, getattr(fallback, f))
    if not merged.line_items and fallback.line_items:
        merged.line_items = fallback.line_items
        if merged.line_items:
            merged.contractor_name = merged.contractor_name or merged.line_items[0].contractor_name
    return merged


def parse_invoice(pdf_path: str, *, allow_llm: bool = True) -> ParseOutcome:
    r = rules.parse_with_rules(pdf_path)
    warnings = list(r.warnings)

    if not (_needs_llm(r) and allow_llm and llm.is_available()):
        return ParseOutcome(r.parsed, r.confidence, "rules", r.has_text, warnings)

    try:
        llm_parsed = llm.parse_with_llm(pdf_path)
    except Exception as e:
        warnings.append(f"LLM fallback failed: {e}")
        return ParseOutcome(r.parsed, r.confidence, "rules", r.has_text, warnings)

    if not r.has_text:
        # Scanned PDF: rules produced nothing, so trust the LLM entirely.
        merged = llm_parsed
        method = "llm"
    else:
        merged = _merge(r.parsed, llm_parsed)
        method = "rules+llm"

    confidence = rules._score(merged, warnings)
    return ParseOutcome(merged, confidence, method, r.has_text, warnings)
