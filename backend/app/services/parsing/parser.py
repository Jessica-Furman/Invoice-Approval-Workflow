"""Hybrid parse orchestrator: rules first, then learned vendor templates, then Claude fallback.

Order per invoice: generic rules (free) -> stored vendor template (free, learned from a previous
LLM parse) -> LLM (only for genuinely new/unparseable layouts). When the LLM does run, its single
call also emits a template that is validated against the same PDF and — via ingestion — stored so
the next invoice from that vendor never needs the LLM again.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.schemas import ParsedInvoice
from app.services.parsing import llm, ocr, rules

if TYPE_CHECKING:  # avoid importing SQLAlchemy at module scope for pure-parsing callers
    from sqlalchemy.orm import Session

# Below this rules-confidence, try the LLM (if a key is configured).
CONFIDENCE_THRESHOLD = 0.8
REQUIRED_FIELDS = ("vendor_name", "invoice_number", "date_received", "total_invoice_cost")


@dataclass
class ParseOutcome:
    parsed: ParsedInvoice
    confidence: float
    method: str  # "rules" | "ocr" | "template" | "llm" | "rules+llm"
    has_text: bool
    warnings: list[str] = field(default_factory=list)
    # Set when a stored vendor template parsed this invoice.
    template_id: int | None = None
    # Set when the LLM ran and its emitted template validated — ingestion persists it.
    learned_template: dict | None = None
    # CAPEX/OPEX / company code / cost center hints the LLM read off the invoice (advisory only).
    llm_accounting: dict | None = None

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


def _has_mojibake_name(parsed: ParsedInvoice) -> bool:
    """True if any contractor name carries U+FFFD — an accented char the text layer couldn't map."""
    if parsed.contractor_name and "�" in parsed.contractor_name:
        return True
    return any(li.contractor_name and "�" in li.contractor_name for li in parsed.line_items)


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


def _try_stored_template(db: "Session", r: rules.RulesResult, warnings: list[str]) -> tuple[rules.RulesResult, int | None]:
    """Apply a stored vendor template when the rules result isn't good enough.

    Returns the (possibly improved) RulesResult and the template id when the template alone made
    the result pass the gate. Any template failure is swallowed — worst case we fall to the LLM.
    """
    from app.services.parsing import templates

    try:
        hit = templates.find_template(db, r.text)
        if hit is None:
            return r, None
        t_parsed = templates.apply_template(hit.template, r.text, r.tables)
        merged = _merge(r.parsed, t_parsed)
        cand = rules.RulesResult(
            merged, rules._score(merged, warnings), warnings, r.text, r.has_text, r.tables
        )
        if not _needs_llm(cand):
            templates.mark_used(db, hit)
            return cand, hit.id
        return cand if cand.confidence > r.confidence else r, None
    except Exception as e:  # a bad template must never break ingestion
        warnings.append(f"Stored template failed: {e}")
        return r, None


def parse_invoice(pdf_path: str, *, allow_llm: bool = True, db: "Session | None" = None) -> ParseOutcome:
    r = rules.parse_with_rules(pdf_path)
    warnings = list(r.warnings)

    # Repair accented contractor names the text layer mangled to U+FFFD (e.g. Cognizant's "Pérez")
    # using OCR, which reads the glyphs correctly. Only runs when a mojibake name is actually present.
    if r.has_text and _has_mojibake_name(r.parsed) and ocr.is_available():
        try:
            ocr_text = ocr.ocr_pdf(pdf_path)
            rules.repair_mojibake_names(r.parsed.line_items, ocr_text)
            if r.parsed.line_items:
                r.parsed.contractor_name = r.parsed.line_items[0].contractor_name
        except Exception as e:  # pragma: no cover - OCR edge cases
            warnings.append(f"OCR name repair failed: {e}")

    # Scanned PDF (no embedded text): try OCR before anything else (no LLM needed).
    if not r.has_text and ocr.is_available():
        try:
            text = ocr.ocr_pdf(pdf_path)
            if text.strip():
                r = rules.parse_from_text(text)
                warnings = list(r.warnings)
                if not _needs_llm(r) or not (allow_llm and llm.is_available()):
                    return ParseOutcome(r.parsed, r.confidence, "ocr", True, warnings)
        except Exception as e:
            warnings.append(f"OCR failed: {e}")

    # Learned vendor templates: free (pure regex), tried only when rules alone weren't enough.
    # Templates target the text layer, so scanned PDFs (no text) skip straight to the LLM.
    if _needs_llm(r) and db is not None and r.has_text:
        r, template_id = _try_stored_template(db, r, warnings)
        if template_id is not None:
            return ParseOutcome(
                r.parsed, r.confidence, "template", True, warnings, template_id=template_id
            )

    if not (_needs_llm(r) and allow_llm and llm.is_available()):
        return ParseOutcome(r.parsed, r.confidence, "ocr" if not r.has_text else "rules", r.has_text, warnings)

    try:
        result = llm.extract_with_llm(pdf_path)
    except Exception as e:
        warnings.append(f"LLM fallback failed: {e}")
        return ParseOutcome(r.parsed, r.confidence, "rules", r.has_text, warnings)

    if not r.has_text:
        # Scanned PDF: rules produced nothing, so trust the LLM entirely.
        merged = result.parsed
        method = "llm"
    else:
        merged = _merge(r.parsed, result.parsed)
        method = "rules+llm"

    # One-and-done learning: keep the emitted template only if it reproduces the LLM's own
    # extraction on this same PDF (and only for text PDFs — templates need a text layer).
    learned = None
    if (
        result.template
        and result.template_confidence == "high"
        and r.has_text
        and merged.vendor_name
    ):
        from app.services.parsing import templates

        ok, reasons = templates.validate_template(result.template, r.text, r.tables, result.parsed)
        if ok:
            learned = result.template
        else:
            warnings.append(f"Learned template failed validation: {'; '.join(reasons)}")

    confidence = rules._score(merged, warnings)
    return ParseOutcome(
        merged, confidence, method, r.has_text, warnings,
        learned_template=learned, llm_accounting=result.accounting,
    )
