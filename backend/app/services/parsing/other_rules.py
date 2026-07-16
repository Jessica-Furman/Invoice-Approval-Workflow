"""Parsing for **"Other Invoice Types"** — hardware / software / subscription invoices.

This is a SEPARATE pipeline from contractor parsing (`rules.py`), triggered only when the user uploads
from the "Other Invoice Types" tab. It extracts, for any vendor: **vendor name, invoice number, invoice
date, grand total, and one-or-more service lines** (service description + optional quantity + optional
unit price + amount). There is no Clarity matching; the supplier number is resolved downstream in
ingestion from `documentation/Active supplier list.csv`.

Robust, tiered extraction so we recover the fields "no matter what":
  1. **Ruled tables** (pdfplumber) — clean column-mapped tables (TowerData, VGS, CyrusOne, GoTo, ...).
  2. **Text layout** — money-anchored line parsing for invoices whose rows aren't a real table
     (GitHub vertical layout, Texas Shred / Bridgepointe / ClearSky / Maven / Stewart columnar text).
  3. **OCR** — for scanned/image PDFs, `ocr_pdf()` then the same text-layout parser.

Header fields (vendor / invoice # / date) reuse the contractor `extract_header`; the grand total uses a
broader labeled-total scan. Nothing here imports or mutates contractor parsing behavior.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import pdfplumber

from app.schemas import ParsedOtherInvoice, ParsedOtherLineItem
from app.services.parsing import ocr
from app.services.parsing.rules import clean_number, extract_header


@dataclass
class OtherParseResult:
    parsed: ParsedOtherInvoice
    method: str            # "rules" | "text" | "ocr"
    has_text: bool
    warnings: list[str] = field(default_factory=list)


# --- money & footer helpers -----------------------------------------------------------------
# A money token: optional $/USD, thousands groups, exactly 2 decimals. The two trailing lookaheads
# reject 3-decimal quantities ("1.000") and dotted dates ("05.15.2026" -> not "05.15").
_MONEY_RE = re.compile(r"(?:USD|US\$|\$)?\s*(\d{1,3}(?:,\d{3})+\.\d{2}|\d+\.\d{2})(?!\d)(?!\.\d)")
# A single cell that is *just* a money value (allows a trailing tax/currency letter like "2,893.62T").
_MONEY_CELL_RE = re.compile(r"^\s*(?:USD|US\$|\$)?\s*\d{1,3}(?:,\d{3})*\.\d{1,3}\s*[A-Za-z]?\s*$")

# Vendor letterhead: legal-entity suffixes (Anglo + a few foreign, e.g. Polish "Sp. z o.o.") we
# truncate the vendor name at, dropping trailing address/remit/account noise on the same line.
_LEGAL_SUFFIX_RE = re.compile(
    r"\b(?:L\.?L\.?C\.?|L\.?L\.?P\.?|Inc\.?|Incorporated|Ltd\.?|Limited|Corp\.?|Corporation|GmbH|PLLC|"
    r"P\.?C\.?|Sp\.?\s*z\s*o\.?\s*o\.?|S\.?A\.?|B\.?V\.?|Pty\.?)\b\.?",
    re.IGNORECASE,
)
_CUSTOMER_RE = re.compile(r"rent-?\s?a-?\s?center|acima|upbound", re.IGNORECASE)
_DOTTED_DATE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
# Explicit "Seller:/Supplier:/Vendor:/Sold By:" label carrying the vendor name.
_VENDOR_LABEL_RE = re.compile(r"\b(?:seller|supplier|vendor|sold\s+by)\s*:?\s*(.+)$", re.IGNORECASE)
# Where the vendor name ends when the same line also carries the customer ("... Buyer: Acima ...").
_BUYER_CUT_RE = re.compile(r"\b(buyer|bill\s*to|sold\s*to|ship\s*to|address|customer)\b", re.IGNORECASE)
# Generic document titles that are never a vendor name.
_GENERIC_TITLE_RE = re.compile(
    r"^(invoice|service\s+invoice|tax\s+invoice|payment\s+instructions|bill|statement|remittance|"
    r"customer|reference|page\b|date\b|invoice\s+no)",
    re.IGNORECASE,
)


def _truncate_suffix(s: str) -> str | None:
    """Trim a candidate vendor string at its legal suffix (keeping the suffix); tidy and validate."""
    s = (s or "").strip(" ,.-")
    m = _LEGAL_SUFFIX_RE.search(s)
    cand = re.sub(r"\s+", " ", (s[: m.end()] if m else s).strip(" ,.-"))
    return cand if re.search(r"[A-Za-z]", cand) and len(cand) >= 3 else None


def _clean_vendor_name(v: str | None) -> str | None:
    """Tidy a vendor name for display + supplier lookup: fold a stylized '@' back to 'a'
    ('TowerD@ta' -> 'TowerData') and keep the legal name before a 'dba' ('X dba Y' -> 'X')."""
    if not v:
        return v
    v = v.replace("@", "a")
    v = re.split(r"\s+dba\s+", v, flags=re.IGNORECASE)[0].strip()
    return v or None


def _extract_vendor(text: str) -> str | None:
    """The supplier's name. Priority: (1) a 'Seller:/Supplier:' label whose value carries a legal
    suffix (handles 'Seller: IRONIN Sp. z o.o. Sp. k. Buyer: ...'); (2) the first non-customer,
    non-title letterhead line carrying a legal suffix, truncated at that suffix."""
    lines = text.splitlines()[:30]
    for line in lines:  # (1) explicit label
        m = _VENDOR_LABEL_RE.search(line)
        if m:
            cand = m.group(1)
            bm = _BUYER_CUT_RE.search(cand)
            if bm:
                cand = cand[: bm.start()]
            if _LEGAL_SUFFIX_RE.search(cand):  # only trust the label when it names a real entity
                out = _truncate_suffix(cand)
                if out:
                    return out
    for line in lines:  # (2) letterhead line with a legal suffix
        s = line.strip()
        if not s or _CUSTOMER_RE.search(s) or _GENERIC_TITLE_RE.match(s):
            continue
        if _LEGAL_SUFFIX_RE.search(s):
            out = _truncate_suffix(s)
            if out:
                return out
    return None


# Vendor brand from an email domain (e.g. accountsreceivable@cyrusone.com -> "CyrusOne"). Used when
# the letterhead legal entity is a payment/billing shell (e.g. "C1 Ground Tenant LLC") that isn't a
# known supplier, but the real brand — printed only in the footer/remit email — is. Bank and generic
# personal domains are ignored so we never pick the remit bank as the vendor.
_EMAIL_DOMAIN_RE = re.compile(r"@([A-Za-z0-9-]+)\.[A-Za-z][A-Za-z.]{1,}")
_NON_VENDOR_DOMAINS = {
    "gmail", "yahoo", "hotmail", "outlook", "live", "aol", "icloud", "me", "msn", "proton",
    "pnc", "pncbank", "wellsfargo", "chase", "bankofamerica", "citibank", "citi", "usbank",
}


def _email_domain_vendors(text: str) -> list[str]:
    """Ordered, de-duped vendor-brand candidates taken from email domains in the invoice text.

    The domain label is cased from an actual text occurrence when possible ('cyrusone' -> 'CyrusOne'),
    else title-cased. Bank/personal domains and very short labels are skipped.
    """
    out: list[str] = []
    seen: set[str] = set()
    for m in _EMAIL_DOMAIN_RE.finditer(text):
        label = m.group(1).lower()
        if label in _NON_VENDOR_DOMAINS or len(label) < 3 or label in seen:
            continue
        seen.add(label)
        out.append(_cased_occurrence(text, label))
    return out


def _cased_occurrence(text: str, label: str) -> str:
    """Proper casing for a domain brand: the first standalone (non-email) occurrence in the text
    ('CyrusOne'), preferring one that carries real casing; else the label title-cased."""
    fallback: str | None = None
    for m in re.finditer(r"\b" + re.escape(label) + r"\b", text, re.IGNORECASE):
        if m.start() > 0 and text[m.start() - 1] == "@":
            continue  # inside an email address -> lowercase, skip
        word = m.group(0)
        if any(c.isupper() for c in word):
            return word
        fallback = fallback or word
    return fallback or label.capitalize()


def _extract_date_other(text: str, header_date):
    """Header date, else a dotted date like '05.15.2026' (American MM.DD.YYYY) that parse_date misses."""
    if header_date is not None:
        return header_date
    from app.services.parsing.rules import parse_date

    m = _DOTTED_DATE_RE.search(text)
    return parse_date(f"{m.group(1)}/{m.group(2)}/{m.group(3)}") if m else None
# Lines that are totals/tax/bank details — never treated as a service line item.
_FOOTER_RE = re.compile(
    r"\b(sub\s*-?\s*total|tax|total\s+due|balance\s+due|amount\s+due|invoice\s+total|grand\s+total|"
    r"total\s+tax|net\s+due|please\s+remit|remit\s+to|routing|swift|aba|account\s*(?:#|number|name)|"
    r"payment\s+terms|bank\s+details|subtotal\s+before)\b",
    re.IGNORECASE,
)
# A money amount anywhere on a total line (for the plain-"Total" scan).
_MONEY_IN = re.compile(r"(?:USD|US\$|\$)?\s*([0-9][0-9,]*\.\d{2})")
# Lines whose "total" is NOT the whole-invoice total: sub-totals, tax, and remaining-balance/payment
# lines (Balance/Amount/Total Due, Total Paid, credits) — excluded so we grab the true invoice total,
# not a payment.
_PLAIN_TOTAL_EXCLUDE = re.compile(
    r"sub\s*-?\s*total|subtotal|tax|total\s+due|balance|amount\s+due|before\s+tax|paid|payment|credit",
    re.IGNORECASE,
)


def _labeled_amount(text: str, label: str) -> float | None:
    """Amount printed after a specific label, e.g. 'Invoice Total: $61,224.55' (last occurrence)."""
    vals = re.findall(label + r"\s*:?\s*(?:USD|US\$|\$)?\s*([0-9][0-9,]*\.\d{2})", text, re.IGNORECASE)
    return clean_number(vals[-1]) if vals else None


def _plain_total(text: str) -> float | None:
    """The amount on a plain 'Total' line (the whole-invoice total), excluding subtotal/tax and
    Balance/Amount/Total Due lines. Takes the last such line, since it sits below any subtotals."""
    best: float | None = None
    for line in text.splitlines():
        if re.search(r"\btotals?\b", line, re.IGNORECASE) and not _PLAIN_TOTAL_EXCLUDE.search(line):
            m = _MONEY_IN.findall(line)
            if m:
                best = clean_number(m[-1])
    return best


def _extract_total(text: str) -> float | None:
    """The total price for the ENTIRE invoice.

    Priority (so a partial 'Balance Due' / 'Amount Due' payment never wins over the real invoice
    total): (1) an explicit 'Invoice Total' / 'Grand Total' label; (2) a plain 'Total' line; only then
    (3) 'Total Due' / 'Balance Due' / 'Amount Due'. When NONE is printed, the caller sums the line
    items instead.
    """
    for label in (r"Invoice\s*Total", r"Grand\s*Total"):
        v = _labeled_amount(text, label)
        if v is not None:
            return v
    v = _plain_total(text)
    if v is not None:
        return v
    for label in (r"Total\s*Due", r"Balance\s*Due", r"Amount\s*Due"):
        v = _labeled_amount(text, label)
        if v is not None:
            return v
    return None


# --- table tier ------------------------------------------------------------------------------
# Column detection is prioritized so, e.g., a "Service Description" column wins over an "Item" code
# column, and the line "Amount"/"Total" wins while Tax/Subtotal columns are excluded.
_DESC_TIERS = [("service description", "description"), ("charge name", "service", "product"), ("item", "details", "activity")]
_QTY_KEYS = ("quantity", "qty", "units")
_PRICE_TIERS = [("unit price",), ("rate", "price")]
_AMOUNT_TIERS = [("amount",), ("total",), ("gross value", "gross"), ("value",), ("charge",), ("net",)]
_AMOUNT_EXCLUDE = ("tax", "subtotal", "sub total", "sub-total", "vat")
_FOOTER_CELL_RE = re.compile(
    r"^\s*(sub\s*-?\s*total|tax|total\s+due|balance\s+due|amount\s+due|invoice\s+total|grand\s+total|total)\b",
    re.IGNORECASE,
)


def _norm_cell(c: str | None) -> str:
    return (c or "").replace("\n", " ").strip()


def _match_tier(header: list[str], tiers: list[tuple[str, ...]], exclude: tuple[str, ...] = ()) -> int | None:
    """First column matching the highest-priority tier of key substrings (skipping excluded headers)."""
    low = [h.lower() for h in header]
    for tier in tiers:
        for i, h in enumerate(low):
            if any(x in h for x in exclude):
                continue
            if any(k in h for k in tier):
                return i
    return None


def _match_any(header: list[str], keys: tuple[str, ...]) -> int | None:
    low = [h.lower() for h in header]
    for i, h in enumerate(low):
        if any(k in h for k in keys):
            return i
    return None


def _match_excl(header: list[str], keys: tuple[str, ...], exclude: tuple[str, ...]) -> int | None:
    low = [h.lower() for h in header]
    for i, h in enumerate(low):
        if any(x in h for x in exclude):
            continue
        if any(k in h for k in keys):
            return i
    return None


def _clean_control(s: str) -> str:
    """Drop control chars (font-ligature artifacts land as \\x00 etc.) and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f]", " ", s or "")).strip()


def _cell(cells: list[str], ci: int | None) -> str:
    return cells[ci] if ci is not None and 0 <= ci < len(cells) else ""


def _find_header_row(table: list[list[str]]) -> tuple[int | None, list[str]]:
    """The first row (within the first 6) that has BOTH a description-ish and an amount-ish column."""
    for i, row in enumerate(table[:6]):
        cells = [_norm_cell(c) for c in row]
        if _match_tier(cells, _DESC_TIERS) is not None and _match_tier(cells, _AMOUNT_TIERS, _AMOUNT_EXCLUDE) is not None:
            return i, [_norm_cell(c) for c in table[i]]
    return None, []


def _tier_rank(header: list[str], tiers: list[tuple[str, ...]], exclude: tuple[str, ...] = ()) -> int:
    """Which tier a header matches (0 = strongest), or len(tiers) if none. Used to rank competing
    tables so a literal 'Description' column outranks a weaker 'Service Type' match."""
    low = [h.lower() for h in header]
    for ti, tier in enumerate(tiers):
        for h in low:
            if any(x in h for x in exclude):
                continue
            if any(k in h for k in tier):
                return ti
    return len(tiers)


def _parse_other_table(table: list[list[str]]) -> list[ParsedOtherLineItem]:
    header_idx, header = _find_header_row(table)
    if header_idx is None:
        return []
    ci_desc = _match_tier(header, _DESC_TIERS)
    # A "Product"/"Charge Name" column to prefix the description with (but never a "... Period" column).
    ci_prod = _match_excl(header, ("product", "charge name"), ("period",))
    if ci_prod == ci_desc:
        ci_prod = None
    ci_qty = _match_any(header, _QTY_KEYS)
    ci_price = _match_tier(header, _PRICE_TIERS, ("unit of measure",))
    ci_amount = _match_tier(header, _AMOUNT_TIERS, _AMOUNT_EXCLUDE)

    items: list[ParsedOtherLineItem] = []
    for row in table[header_idx + 1:]:
        cells = [_norm_cell(c) for c in row]
        if not any(cells):
            continue
        amount_raw = _cell(cells, ci_amount)
        if not _MONEY_CELL_RE.match(amount_raw):  # reject garbled/blob "tables"
            continue
        desc = _cell(cells, ci_desc)
        prod = _cell(cells, ci_prod)
        if prod and prod.lower() != desc.lower():
            desc = f"{prod} - {desc}".strip(" -") if desc else prod
        desc = _clean_control(desc)
        if not desc or _FOOTER_CELL_RE.match(desc) or not re.search(r"[A-Za-z]", desc):
            continue
        items.append(
            ParsedOtherLineItem(
                description=re.sub(r"\s+", " ", desc).strip(),
                quantity=clean_number(_cell(cells, ci_qty)),
                unit_price=clean_number(_cell(cells, ci_price)),
                amount=clean_number(amount_raw),
            )
        )
    return items


def _line_items_from_tables(tables: list[list[list[str]]]) -> list[ParsedOtherLineItem]:
    """Pick the best service table. An invoice can carry supporting *detail* tables (e.g. a per-ticket
    appendix) with MORE rows than the billing-summary table; ranking by row count alone would wrongly
    pick the appendix (the CyrusOne 'Smarthands' case). So rank by description-column strength first —
    a literal 'Description' column beats a weaker 'Service Type' match — then by row count."""
    best: list[ParsedOtherLineItem] = []
    best_key: tuple[int, int] | None = None
    for t in tables:
        items = _parse_other_table(t)
        if not items:
            continue
        _, header = _find_header_row(t)
        key = (_tier_rank(header, _DESC_TIERS), -len(items))
        if best_key is None or key < best_key:
            best_key, best = key, items
    return best


# --- word-position tier (generic column reconstruction) --------------------------------------
# Vendor-agnostic fallback: when a table collapses (pdfplumber merges the row into one cell) or a row
# has many numeric columns the text tier can't split (Salesforce: Service|Quote#|Months|Qty|Unit
# Price|Tax Rate|Tax|Total), rebuild columns from the words' x-coordinates. The header row's words
# define the columns; each body word is assigned to the nearest column by x-center. No per-vendor
# rules — it reads whatever columns the invoice prints.
_LEADING_LINENO_RE = re.compile(r"^\s*\d{1,3}\s+(?=[A-Za-z])")  # a leading line number: "1 Additional …"
# The true end of the line-items region (a grand-total/remaining-balance line). NOT a plain "Total",
# since some invoices (Salesforce) print a per-line "Tax Breakdown" between items.
_WORD_SECTION_END_RE = re.compile(
    r"^(invoice\s+total|grand\s+total|balance\s+due|amount\s+due|total\s+due|subtotal|sub\s*-?\s*total)\b",
    re.IGNORECASE,
)


def _group_words_into_lines(words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
    """Group extracted words into visual rows by their vertical position, each row sorted left→right."""
    lines: list[dict] = []
    cur: dict | None = None
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        if cur is None or abs(w["top"] - cur["top"]) > y_tol:
            cur = {"top": w["top"], "words": [w]}
            lines.append(cur)
        else:
            cur["words"].append(w)
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
    return [ln["words"] for ln in lines]


def _segment_row(words: list[dict], min_gap: float = 9.0) -> list[str]:
    """Split a visual row into column cells at large horizontal gaps. Adapts per-row (column gaps are
    much wider than the spaces between words in a cell), so it handles both left-aligned text and
    right-aligned numbers without needing fixed column boundaries."""
    if not words:
        return []
    gaps = sorted(words[i + 1]["x0"] - words[i]["x1"] for i in range(len(words) - 1))
    # Threshold between intra-cell spaces (small) and column gaps (large): anchor on a low-percentile
    # gap (a within-cell space) times a factor, so column gaps clear it even when a row is mostly gaps.
    thr = max(min_gap, gaps[len(gaps) // 4] * 2.5) if gaps else min_gap
    cells = [words[0]["text"]]
    for i in range(1, len(words)):
        if words[i]["x0"] - words[i - 1]["x1"] > thr:
            cells.append(words[i]["text"])
        else:
            cells[-1] += " " + words[i]["text"]
    return [c.strip() for c in cells]


def _line_items_from_words(pages_words: list[list[dict]]) -> list[ParsedOtherLineItem]:
    """Reconstruct line items from word positions. Finds the columnar header once, maps its cells to
    roles (desc / qty / unit price / amount), then segments each body row the same way. Rows whose cell
    count matches the header map straight across; otherwise we anchor on the first cell (description)
    and the last money cell (amount)."""
    labels: list[str] | None = None
    di = ai = qi = pi = None
    items: list[ParsedOtherLineItem] = []
    pending: str | None = None
    last: ParsedOtherLineItem | None = None

    for words in pages_words:
        if not words:
            continue
        lines = _group_words_into_lines(words)
        start = 0
        if labels is None:  # locate the columnar header (first page that has one)
            for i, ln in enumerate(lines):
                text = " ".join(w["text"] for w in ln)
                if len(ln) >= 3 and _SECTION_HEADER_RE.search(text) and not _MONEY_RE.search(text):
                    labels = _segment_row(ln)
                    di = _match_tier(labels, _DESC_TIERS)
                    ai = _match_tier(labels, _AMOUNT_TIERS, _AMOUNT_EXCLUDE)
                    qi = _match_any(labels, _QTY_KEYS)
                    pi = _match_tier(labels, _PRICE_TIERS, ("unit of measure",))
                    start = i + 1
                    break
            if labels is None or di is None or ai is None:
                labels = None
                continue

        for ln in lines[start:]:
            text = " ".join(w["text"] for w in ln).strip()
            if not text:
                continue
            if _WORD_SECTION_END_RE.match(text):
                return items  # reached the totals section
            if _SECTION_HEADER_RE.search(text) and not _MONEY_RE.search(text):
                continue  # a repeated header on a later page
            cells = _segment_row(ln)
            # A leading line number ("1", "2", …) often segments as its own cell, making the row one
            # cell wider than the header; drop it so the remaining cells align to the columns.
            if len(cells) == len(labels) + 1 and re.fullmatch(r"\d{1,3}", cells[0]):
                cells = cells[1:]

            if len(cells) == len(labels):
                amount_raw = cells[ai]
                desc_raw = cells[di]
                qty_raw = cells[qi] if qi is not None else ""
                price_raw = cells[pi] if pi is not None else ""
            else:  # misaligned row: anchor on first cell + last money cell
                money = [c for c in cells if _MONEY_CELL_RE.match(c)]
                amount_raw = money[-1] if money else ""
                desc_raw = cells[0] if cells else ""
                qty_raw = price_raw = ""

            amount = clean_number(amount_raw) if _MONEY_CELL_RE.match(amount_raw) else None
            desc = _LEADING_LINENO_RE.sub("", desc_raw).strip()
            is_footer = bool(_FOOTER_RE.search(text))

            if amount is None:
                # A description that wrapped onto its own line (no money, alpha only, no stray digits).
                if desc and re.search(r"[A-Za-z]", desc) and not is_footer and not re.search(r"\d", text):
                    if last is not None and pending is None:
                        last.description = re.sub(r"\s+", " ", f"{last.description} {desc}").strip()
                    else:
                        pending = f"{pending} {desc}".strip() if pending else desc
                continue
            if is_footer or not re.search(r"[A-Za-z]", desc):
                continue
            full = f"{pending} {desc}".strip() if pending else desc
            pending = None
            last = ParsedOtherLineItem(
                description=re.sub(r"\s+", " ", full).strip(),
                quantity=clean_number(qty_raw),
                unit_price=clean_number(price_raw),
                amount=amount,
            )
            items.append(last)
    return items


def _sum_amounts(items: list[ParsedOtherLineItem]) -> float:
    return round(sum(li.amount or 0.0 for li in items), 2)


def _choose_line_items(
    candidates: list[tuple[str, list[ParsedOtherLineItem]]], total: float | None
) -> tuple[list[ParsedOtherLineItem], str]:
    """Pick the best line-item set. When the invoice total is known, prefer the set whose amounts sum
    closest to it (this is how the generic word tier wins over a collapsed table on Salesforce). On an
    equal sum, prefer MORE line items — a set that splits a collapsed blob into its real rows is more
    useful and, summing identically, no less accurate. With no total, most line items wins."""
    best_items: list[ParsedOtherLineItem] = []
    best_label = "rules"
    best_key: tuple[float, int] | None = None
    for label, items in candidates:
        if not items:
            continue
        close = abs(_sum_amounts(items) - total) if total else 0.0
        key = (round(close, 2), -len(items))
        if best_key is None or key < best_key:
            best_key, best_items, best_label = key, items, label
    return best_items, best_label


# --- text tier -------------------------------------------------------------------------------
# A trailing "<qty>? <unit price>? <amount>" run at the end of a columnar text row (Texas Shred,
# Bridgepointe, ClearSky, Maven). qty may be a bare/3-decimal number; price & amount are money.
_ROW_TAIL_RE = re.compile(
    r"^(?P<desc>.*?[A-Za-z].*?)\s+"
    r"(?:(?P<qty>\d[\d,]*(?:\.\d+)?)\s+)?"
    r"(?:(?:USD|US\$|\$)\s*(?P<price>\d[\d,]*\.\d{2})\s+)?"
    r"(?:USD|US\$|\$)?\s*(?P<amount>\d[\d,]*\.\d{2})(?:[A-Z])?\s*$"
)
_LEADING_INDEX_RE = re.compile(r"^\s*\d+\.\s+")                       # "1. " row number
_LEADING_DATE_RE = re.compile(r"^\s*\d{1,2}/\d{1,2}/\d{2,4}\s+")      # "04/02/2026 "


def _clean_desc(desc: str) -> str:
    desc = _LEADING_INDEX_RE.sub("", desc)
    desc = _LEADING_DATE_RE.sub("", desc)
    return _clean_control(desc)


# The line-items section starts at a header row that names a description column AND a money column.
_SECTION_HEADER_RE = re.compile(
    r"(?=.*\b(description|service|product|item|charge)\b)(?=.*\b(amount|total|price|rate|charge)\b)",
    re.IGNORECASE,
)
# A totals boundary that ends the line-items section.
_SECTION_END_RE = re.compile(
    r"^\s*(sub\s*-?\s*total|subtotal|tax|total\b|balance\s+due|amount\s+due|invoice\s+total|grand\s+total|currency\s*:)",
    re.IGNORECASE,
)


def _line_items_from_text(text: str) -> list[ParsedOtherLineItem]:
    """Money-anchored parsing of the line-items *section*. We bound to the region after a
    "Description ... Amount"-style header and before the totals, then handle two row shapes:
    columnar rows ending in a money amount, and vertical layout (GitHub) where a money-only line
    follows its description line.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    start = 0
    for i, s in enumerate(lines):
        if s and _SECTION_HEADER_RE.search(s) and not _MONEY_RE.search(s):
            start = i + 1
            break

    items: list[ParsedOtherLineItem] = []
    pending_desc: str | None = None  # last description-only line, for the vertical layout / wraps
    for s in lines[start:]:
        if not s:
            pending_desc = None
            continue
        if _SECTION_END_RE.match(s):
            break
        is_footer = bool(_FOOTER_RE.search(s))
        has_money = bool(_MONEY_RE.search(s))
        has_alpha = bool(re.search(r"[A-Za-z]", s))

        if has_money and not is_footer:
            money = _MONEY_RE.findall(s)
            text_wo_money = _MONEY_RE.sub("", s).strip()
            if not re.search(r"[A-Za-z]", text_wo_money):
                # money-only line -> pair with the preceding description (GitHub vertical layout)
                if pending_desc:
                    items.append(ParsedOtherLineItem(
                        description=_clean_desc(pending_desc), amount=clean_number(money[-1])))
                pending_desc = None
                continue
            m = _ROW_TAIL_RE.match(s)
            if m and re.search(r"[A-Za-z]", m.group("desc")):
                desc = m.group("desc")
                qty = clean_number(m.group("qty"))
                unit_price = clean_number(m.group("price"))
                amount = clean_number(m.group("amount"))
            else:
                desc, qty, unit_price, amount = text_wo_money, None, None, clean_number(money[-1])
            # a description that wrapped onto the previous (money-less) line: prepend it
            if pending_desc:
                desc = f"{pending_desc} {desc}"
            items.append(ParsedOtherLineItem(
                description=_clean_desc(desc), quantity=qty, unit_price=unit_price, amount=amount))
            pending_desc = None
        elif has_alpha and not is_footer:
            pending_desc = s
        else:
            pending_desc = None
    return items


# --- invoice-number fallback (from the file name) --------------------------------------------
_FILENAME_INV_RE = re.compile(r"([A-Za-z]{0,4}\d[\w-]{3,})")


def _invoice_no_from_filename(pdf_path: str) -> str | None:
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    m = _FILENAME_INV_RE.search(stem)
    return m.group(1) if m else None


# --- entrypoint ------------------------------------------------------------------------------
def parse_other_invoice(pdf_path: str) -> OtherParseResult:
    warnings: list[str] = []
    text_parts: list[str] = []
    tables: list[list[list[str]]] = []
    pages_words: list[list[dict]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
            try:
                tables.extend(page.extract_tables() or [])
            except Exception as e:  # pragma: no cover - pdfplumber edge cases
                warnings.append(f"Table extraction error: {e}")
            try:
                pages_words.append(page.extract_words() or [])
            except Exception as e:  # pragma: no cover - pdfplumber edge cases
                pages_words.append([])
                warnings.append(f"Word extraction error: {e}")
    text = "\n".join(text_parts).strip()
    has_text = bool(text)
    method = "rules"

    if not has_text:  # scanned/image PDF -> OCR, then parse from text only
        method = "ocr"
        if ocr.is_available():
            try:
                text = ocr.ocr_pdf(pdf_path)
            except Exception as e:
                warnings.append(f"OCR failed: {e}")
        else:
            warnings.append("Scanned PDF and OCR unavailable.")

    header = extract_header(text)
    # The invoice total is resolved first (independent of line items) so it can arbitrate between the
    # parsing tiers — the set whose amounts sum closest to it wins.
    total = _extract_total(text)
    if total is None:
        total = header.get("total_invoice_cost")

    # Three vendor-agnostic tiers; the trusted table tier is listed first so it wins exact ties.
    candidates: list[tuple[str, list[ParsedOtherLineItem]]] = []
    if tables:
        candidates.append(("rules", _line_items_from_tables(tables)))
    candidates.append(("text", _line_items_from_text(text)))
    if pages_words and has_text:  # word positions only exist for real text PDFs (not OCR output)
        candidates.append(("words", _line_items_from_words(pages_words)))
    line_items, chosen = _choose_line_items(candidates, total)
    if line_items and has_text:
        method = chosen

    if total is None and line_items:  # last resort: sum the line amounts
        s = sum((li.amount or 0.0) for li in line_items)
        total = round(s, 2) if s else None

    vendor = _clean_vendor_name(_extract_vendor(text) or header.get("vendor_name"))
    if vendor and _GENERIC_TITLE_RE.match(vendor.strip()):
        vendor = None  # never show a document title ("SERVICE INVOICE") as the vendor
    # If the letterhead entity isn't a known supplier (e.g. a billing shell like "C1 Ground Tenant
    # LLC"), prefer an email-domain brand that IS in the supplier list (e.g. "CyrusOne").
    from app.services.coupa import supplier_number_for

    if not (vendor and supplier_number_for(vendor)):
        for cand in _email_domain_vendors(text):
            cand = _clean_vendor_name(cand)
            if cand and supplier_number_for(cand):
                vendor = cand
                break
    parsed = ParsedOtherInvoice(
        vendor_name=vendor,
        invoice_number=header.get("invoice_number") or _invoice_no_from_filename(pdf_path),
        date_received=_extract_date_other(text, header.get("date_received")),
        total_invoice_cost=total,
        line_items=line_items,
    )
    return OtherParseResult(parsed, method=method, has_text=has_text, warnings=warnings)


# Required fields for the "All Data Found" column. Quantity & unit price are intentionally optional.
def required_missing_fields(parsed: ParsedOtherInvoice, supplier_number: str | None) -> list[str]:
    """Human-readable list of required fields that are absent (drives Missing Data vs All Data Found)."""
    missing: list[str] = []
    if not parsed.vendor_name:
        missing.append("vendor name")
    if not supplier_number:
        missing.append("supplier number")
    if not parsed.invoice_number:
        missing.append("invoice number")
    if not any((li.description or "").strip() for li in parsed.line_items):
        missing.append("service description")
    if parsed.total_invoice_cost is None:
        missing.append("total price")
    if not parsed.date_received:
        missing.append("date received")
    return missing
