"""Learned vendor parse templates: execute, validate, find, and store.

A template is a small declarative JSON the LLM emits alongside its extraction (see llm.py). It
describes how to parse ONE vendor's layout: per-header-field strategies (constant / regex / absent)
and a line-item strategy (line_regex with named groups, or table_columns header mapping).

Templates are layout-only by design — every captured value goes through the same normalizers the
rules engine uses (rules.clean_number / rules.parse_date), so number/date handling never depends on
the LLM getting formats right. A template is stored only after validate_template() re-parses the
source PDF with it and the output matches the LLM's own extraction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.schemas import ParsedInvoice, ParsedLineItem
from app.services.parsing import rules
from app.utils.names import normalize_name

TEMPLATE_VERSION = 1
MAX_PATTERN_LEN = 512

_HEADER_FIELDS = ("vendor_name", "invoice_number", "date_received", "payment_period", "total_invoice_cost")
_LINE_GROUPS = ("name", "hours", "rate", "amount")


class TemplateError(ValueError):
    """Raised when a template is structurally invalid or a regex won't compile."""


@dataclass
class CompiledTemplate:
    raw: dict
    fingerprint: re.Pattern
    header: dict[str, dict]  # field -> {"strategy", "value"|compiled pattern, "group", "labeled"}
    line_strategy: str  # "line_regex" | "table_columns"
    line_pattern: re.Pattern | None
    columns: dict[str, str | None] | None
    skip_row: re.Pattern | None


def _compile(pattern: str, what: str) -> re.Pattern:
    if not pattern or len(pattern) > MAX_PATTERN_LEN:
        raise TemplateError(f"{what}: pattern missing or longer than {MAX_PATTERN_LEN} chars")
    try:
        return re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    except re.error as e:
        raise TemplateError(f"{what}: regex does not compile ({e})")


def compile_template(t: dict) -> CompiledTemplate:
    """Validate the template shape and compile every regex. Raises TemplateError on any problem."""
    if not isinstance(t, dict):
        raise TemplateError("template is not an object")
    if t.get("template_version") != TEMPLATE_VERSION:
        raise TemplateError(f"unsupported template_version {t.get('template_version')!r}")

    fingerprint = _compile(t.get("fingerprint_regex") or "", "fingerprint_regex")

    header_spec = t.get("header") or {}
    header: dict[str, dict] = {}
    for f in _HEADER_FIELDS:
        spec = header_spec.get(f) or {"strategy": "absent"}
        strategy = spec.get("strategy")
        if strategy == "constant":
            if not spec.get("value"):
                raise TemplateError(f"header.{f}: constant strategy without a value")
            header[f] = {"strategy": "constant", "value": spec["value"]}
        elif strategy == "regex":
            pat = _compile(spec.get("pattern") or "", f"header.{f}")
            if pat.groups < 1:
                raise TemplateError(f"header.{f}: pattern has no capture group")
            header[f] = {
                "strategy": "regex",
                "pattern": pat,
                "group": int(spec.get("group") or 1),
                "labeled": bool(spec.get("labeled")),
            }
        elif strategy == "absent":
            header[f] = {"strategy": "absent"}
        else:
            raise TemplateError(f"header.{f}: unknown strategy {strategy!r}")

    li = t.get("line_items") or {}
    strategy = li.get("strategy")
    line_pattern = None
    columns = None
    if strategy == "line_regex":
        line_pattern = _compile(li.get("pattern") or "", "line_items.pattern")
        missing = [g for g in ("name",) if g not in line_pattern.groupindex]
        if missing:
            raise TemplateError(f"line_items.pattern: missing named group(s) {missing}")
    elif strategy == "table_columns":
        columns = li.get("columns") or {}
        if not columns.get("name"):
            raise TemplateError("line_items.columns: 'name' header keyword is required")
    else:
        raise TemplateError(f"line_items: unknown strategy {strategy!r}")

    skip_row = None
    if li.get("skip_row_regex"):
        skip_row = _compile(li["skip_row_regex"], "line_items.skip_row_regex")

    return CompiledTemplate(
        raw=t,
        fingerprint=fingerprint,
        header=header,
        line_strategy=strategy,
        line_pattern=line_pattern,
        columns=columns,
        skip_row=skip_row,
    )


# --- execution ---------------------------------------------------------------
def _header_value(spec: dict, text: str) -> str | None:
    if spec["strategy"] == "constant":
        return spec["value"]
    if spec["strategy"] == "regex":
        m = spec["pattern"].search(text)
        if m:
            try:
                v = m.group(spec["group"])
            except (IndexError, re.error):  # bad group index from the LLM
                return None
            return v.strip() if v else None
    return None


def _items_from_line_regex(ct: CompiledTemplate, text: str) -> list[ParsedLineItem]:
    items: list[ParsedLineItem] = []
    for m in ct.line_pattern.finditer(text):
        g = m.groupdict()
        if ct.skip_row and ct.skip_row.search(m.group(0)):
            continue
        name = (g.get("name") or "").strip()
        if not name or not re.search(r"[A-Za-z]", name):
            continue
        hours = rules.clean_number(g.get("hours"))
        rate = rules.clean_number(g.get("rate"))
        amount = rules.clean_number(g.get("amount"))
        if hours is None and rate is None and amount is None:
            continue
        if amount is None and hours is not None and rate is not None:
            amount = round(hours * rate, 2)
        extra: dict = {}
        for k in ("period_start", "period_end"):
            d = rules.parse_date(g.get(k)) if g.get(k) else None
            if d:
                extra[k] = d.isoformat()
        items.append(ParsedLineItem(contractor_name=name, hours=hours, rate=rate, amount=amount, extra=extra))
    return items


def _items_from_table_columns(ct: CompiledTemplate, tables: list) -> list[ParsedLineItem]:
    cols = {k: (v or "").lower() for k, v in (ct.columns or {}).items() if v}
    best: list[ParsedLineItem] = []
    for table in tables or []:
        header_idx, mapping = None, {}
        for i, row in enumerate(table[:5]):
            cells = [(c or "").lower() for c in row]
            m = {}
            for role, kw in cols.items():
                for j, cell in enumerate(cells):
                    if kw in cell:
                        m[role] = j
                        break
            if "name" in m:
                header_idx, mapping = i, m
                break
        if header_idx is None:
            continue
        items: list[ParsedLineItem] = []
        for row in table[header_idx + 1 :]:
            cells = [(c or "").strip() for c in row]
            if not any(cells):
                continue
            joined = " ".join(cells)
            if ct.skip_row and ct.skip_row.search(joined):
                continue
            def cell(role: str) -> str | None:
                j = mapping.get(role)
                return cells[j] if j is not None and j < len(cells) else None

            raw_name = cell("name") or ""
            name = rules.extract_person_name(raw_name) or raw_name.strip()
            if not name or not re.search(r"[A-Za-z]", name):
                continue
            if re.match(r"(grand\s+total|sub\s*total|total|balance|amount\s+due|tax)\b", name, re.IGNORECASE):
                continue
            hours = rules.clean_number(cell("hours"))
            rate = rules.clean_number(cell("rate"))
            amount = rules.clean_number(cell("amount"))
            if hours is None and rate is None and amount is None:
                continue
            if amount is None and hours is not None and rate is not None:
                amount = round(hours * rate, 2)
            items.append(ParsedLineItem(contractor_name=name, hours=hours, rate=rate, amount=amount))
        if len(items) > len(best):
            best = items
    return best


def apply_template(t: dict, text: str, tables: list | None = None) -> ParsedInvoice:
    """Execute a template against a PDF's extracted text (+ pdfplumber tables). Raises TemplateError."""
    ct = compile_template(t)

    header = {f: _header_value(spec, text) for f, spec in ct.header.items()}
    if ct.line_strategy == "line_regex":
        items = _items_from_line_regex(ct, text)
    else:
        items = _items_from_table_columns(ct, tables or [])

    total = rules.clean_number(header["total_invoice_cost"])
    if total is None and items:
        s = sum((li.amount or 0) for li in items)
        if s:
            total = round(s, 2)

    parsed = ParsedInvoice(
        vendor_name=header["vendor_name"],
        invoice_number=header["invoice_number"],
        date_received=rules.parse_date(header["date_received"]),
        payment_period=header["payment_period"],
        payment_period_labeled=bool(ct.header["payment_period"].get("labeled")),
        total_invoice_cost=total,
        line_items=items,
    )
    if items:
        parsed.contractor_name = items[0].contractor_name
        parsed.hourly_or_fixed_rate = items[0].rate
        parsed.hours_worked = items[0].hours
    return parsed


# --- validation (before a template is trusted) --------------------------------
def _totals_close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a == b
    return abs(a - b) <= max(1.0, 0.005 * max(abs(a), abs(b)))


def validate_template(t: dict, text: str, tables: list | None, llm_parsed: ParsedInvoice) -> tuple[bool, list[str]]:
    """Re-parse the source document with the template and compare to the LLM's own extraction.

    Returns (ok, reasons). Only a template that reproduces the LLM's result on the same PDF is
    trusted for future invoices.
    """
    from rapidfuzz import fuzz

    reasons: list[str] = []
    try:
        got = apply_template(t, text, tables)
    except TemplateError as e:
        return False, [str(e)]

    if llm_parsed.vendor_name:
        if not got.vendor_name:
            reasons.append("vendor_name not reproduced")
        elif fuzz.token_sort_ratio(got.vendor_name.lower(), llm_parsed.vendor_name.lower()) < 90:
            reasons.append(f"vendor_name mismatch: {got.vendor_name!r} vs {llm_parsed.vendor_name!r}")

    def norm_inv(s: str | None) -> str:
        return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

    if llm_parsed.invoice_number and norm_inv(got.invoice_number) != norm_inv(llm_parsed.invoice_number):
        reasons.append(f"invoice_number mismatch: {got.invoice_number!r} vs {llm_parsed.invoice_number!r}")

    if llm_parsed.date_received and got.date_received != llm_parsed.date_received:
        reasons.append(f"date_received mismatch: {got.date_received} vs {llm_parsed.date_received}")

    if not _totals_close(got.total_invoice_cost, llm_parsed.total_invoice_cost):
        reasons.append(
            f"total mismatch: {got.total_invoice_cost} vs {llm_parsed.total_invoice_cost}"
        )

    if len(got.line_items) != len(llm_parsed.line_items):
        reasons.append(f"line count mismatch: {len(got.line_items)} vs {len(llm_parsed.line_items)}")
    else:
        got_sum = sum((li.amount or 0) for li in got.line_items)
        llm_sum = sum((li.amount or 0) for li in llm_parsed.line_items)
        if not _totals_close(got_sum, llm_sum):
            reasons.append(f"line amount sum mismatch: {got_sum:.2f} vs {llm_sum:.2f}")

    return (not reasons), reasons


# --- storage / lookup ----------------------------------------------------------
def find_template(db: Session, text: str) -> models.VendorParseTemplate | None:
    """First validated template whose fingerprint matches the document text."""
    rows = db.execute(
        select(models.VendorParseTemplate).where(models.VendorParseTemplate.validated.is_(True))
    ).scalars().all()
    for row in rows:
        try:
            if re.search(row.fingerprint_regex, text, re.IGNORECASE):
                return row
        except re.error:
            continue  # one bad stored regex must never break ingestion
    return None


def mark_used(db: Session, tpl: models.VendorParseTemplate) -> None:
    tpl.hit_count = (tpl.hit_count or 0) + 1
    tpl.last_used_at = datetime.now(timezone.utc)


def save_template(
    db: Session,
    vendor_name: str,
    template: dict,
    *,
    source_invoice_id: int | None = None,
    llm_model: str | None = None,
) -> models.VendorParseTemplate:
    """Upsert a validated template keyed by normalized vendor name (newer supersedes older)."""
    vendor_key = normalize_name(vendor_name) or vendor_name.strip().lower()
    row = db.execute(
        select(models.VendorParseTemplate).where(models.VendorParseTemplate.vendor_key == vendor_key)
    ).scalar_one_or_none()
    if row is None:
        row = models.VendorParseTemplate(vendor_key=vendor_key)
        db.add(row)
    row.vendor_name = vendor_name
    row.fingerprint_regex = template.get("fingerprint_regex") or ""
    row.template = template
    row.llm_model = llm_model
    row.source_invoice_id = source_invoice_id
    row.validated = True
    return row
