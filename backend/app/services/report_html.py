"""Self-contained standalone HTML for the executive invoice report.

Built entirely in Python from the aggregates dict (see reporting.py) + the LLM narrative:
one inline <style> block, inline SVG charts, native <title> hover tooltips — zero external
requests, so the file can be emailed and opened offline.

Deliberately light-mode-only: this is an email/print document, not an app surface.
Chart colors are the validated categorical palette (blue/green/yellow pass CVD + normal-vision
checks; yellow is sub-3:1 contrast so every yellow mark carries a visible direct label).
"""
from __future__ import annotations

import html
import math
import re

# Validated palette (dataviz reference instance, light mode).
BLUE = "#2a78d6"
GREEN = "#008300"
YELLOW = "#eda100"
MUTED = "#898781"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
LIME = "#a4d61e"  # InVoicee brand accent (headings/rules only, never a data series)

_CSS = f"""
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; margin: 0; }}
body {{
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: {PAGE}; color: {INK}; padding: 32px 16px; line-height: 1.5;
}}
.page {{ max-width: 920px; margin: 0 auto; }}
header.report {{ border-bottom: 3px solid {LIME}; padding-bottom: 16px; margin-bottom: 24px; }}
header.report h1 {{ font-size: 26px; font-weight: 700; }}
header.report .sub {{ color: {INK2}; font-size: 13px; margin-top: 4px; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.tile {{ background: {SURFACE}; border: 1px solid rgba(11,11,11,0.10); border-radius: 10px; padding: 14px 16px; }}
.tile .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: {MUTED}; }}
.tile .value {{ font-size: 26px; font-weight: 700; margin-top: 2px; }}
.tile .hint {{ font-size: 12px; color: {INK2}; margin-top: 2px; }}
.card {{ background: {SURFACE}; border: 1px solid rgba(11,11,11,0.10); border-radius: 10px; padding: 18px; margin-bottom: 18px; }}
.card h2 {{ font-size: 15px; font-weight: 600; margin-bottom: 12px; }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
@media (max-width: 720px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
.chart-scroll {{ overflow-x: auto; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: {INK2}; margin-top: 10px; }}
.legend .swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: baseline; }}
.narrative h2 {{ font-size: 17px; font-weight: 700; margin: 20px 0 8px; padding-top: 12px; border-top: 1px solid {GRID}; }}
.narrative h3 {{ font-size: 14px; font-weight: 600; margin: 14px 0 6px; }}
.narrative p {{ margin: 8px 0; font-size: 14px; color: {INK}; }}
.narrative ul {{ margin: 8px 0 8px 22px; font-size: 14px; }}
.narrative li {{ margin: 4px 0; }}
footer.report {{ color: {MUTED}; font-size: 11px; margin-top: 28px; text-align: center; }}
svg text {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
"""


def _money(n: float | None) -> str:
    if n is None:
        return "—"
    return f"${n:,.2f}"


def _compact(n: float) -> str:
    if abs(n) >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n / 1_000:.0f}K"
    return f"${n:,.0f}"


def _esc(s: object) -> str:
    return html.escape(str(s))


# --- markdown -> HTML (headings / bullets / bold only — narrative is trusted-model output but
# escaped anyway) ---------------------------------------------------------------------------
def _md_to_html(md: str) -> str:
    out: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def inline(s: str) -> str:
        s = _esc(s)
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    for line in md.splitlines():
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        if stripped.startswith("### "):
            close_list()
            out.append(f"<h3>{inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_list()
            out.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
        else:
            close_list()
            out.append(f"<p>{inline(stripped)}</p>")
    close_list()
    return "\n".join(out)


# --- SVG helpers ------------------------------------------------------------------------------
_CAPEX_BUCKETS = [
    # (aggregate key, display label, color)
    ("CAPEX", "CAPEX", BLUE),
    ("OPEX", "OPEX", GREEN),
    ("vendor_stated_capex", "Vendor-stated CAPEX", YELLOW),
    ("vendor_stated_opex", "Vendor-stated OPEX", YELLOW),
    ("unclassified", "Unclassified", MUTED),
]


def _donut_svg(amounts: dict[str, float]) -> str:
    rows = [(label, amounts.get(key, 0.0), color) for key, label, color in _CAPEX_BUCKETS
            if amounts.get(key, 0.0) > 0]
    total = sum(v for _, v, _ in rows)
    if not total:
        return f'<p style="color:{MUTED};font-size:13px">No classified spend in this period.</p>'

    cx = cy = 90
    r = 62
    stroke = 30
    circ = 2 * math.pi * r
    gap = 2.0  # px surface gap between segments
    parts: list[str] = []
    offset = circ * 0.25  # start at 12 o'clock
    for label, value, color in rows:
        seg = circ * value / total
        dash = max(seg - gap, 0.1)
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {circ - dash:.2f}" '
            f'stroke-dashoffset="{offset:.2f}"><title>{_esc(label)}: {_money(value)} '
            f'({100 * value / total:.1f}%)</title></circle>'
        )
        offset -= seg
    center = (
        f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-size="15" font-weight="700" '
        f'fill="{INK}">{_compact(total)}</text>'
        f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="10" fill="{MUTED}">classified</text>'
    )
    # Visible per-bucket labels (relief rule: yellow is sub-3:1, so values never rely on color).
    legend = "".join(
        f'<div><span class="swatch" style="background:{color}"></span>'
        f'{_esc(label)} — <strong>{_money(value)}</strong> ({100 * value / total:.1f}%)</div>'
        for label, value, color in rows
    )
    return (
        f'<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">'
        f'<svg width="180" height="180" viewBox="0 0 180 180" role="img" '
        f'aria-label="CAPEX vs OPEX split">{"".join(parts)}{center}</svg>'
        f'<div class="legend" style="flex-direction:column;gap:6px">{legend}</div></div>'
    )


def _rounded_bar(x: float, y: float, w: float, h: float, color: str, title: str) -> str:
    """Horizontal bar anchored square at the baseline, 4px rounded data-end."""
    r = min(4.0, w / 2, h / 2)
    d = (f"M{x:.1f} {y:.1f} h{w - r:.1f} q{r:.1f} 0 {r:.1f} {r:.1f} v{h - 2 * r:.1f} "
         f"q0 {r:.1f} -{r:.1f} {r:.1f} h-{w - r:.1f} z")
    return f'<path d="{d}" fill="{color}"><title>{title}</title></path>'


def _hbar_svg(rows: list[tuple[str, float]], color: str = BLUE) -> str:
    """Single-series horizontal bar chart (magnitude): one hue, direct value labels."""
    if not rows:
        return f'<p style="color:{MUTED};font-size:13px">No data in this period.</p>'
    label_w, value_w = 170, 78
    bar_h, gap = 20, 10
    chart_w = 640
    max_v = max(v for _, v in rows) or 1
    bar_max = chart_w - label_w - value_w
    height = len(rows) * (bar_h + gap)
    parts = [f'<line x1="{label_w}" y1="0" x2="{label_w}" y2="{height - gap}" stroke="{BASELINE}" stroke-width="1"/>']
    for i, (name, v) in enumerate(rows):
        y = i * (bar_h + gap)
        w = max(bar_max * v / max_v, 2)
        short = name if len(name) <= 24 else name[:23] + "…"
        parts.append(
            f'<text x="{label_w - 8}" y="{y + bar_h / 2 + 4}" text-anchor="end" font-size="12" '
            f'fill="{INK2}">{_esc(short)}</text>'
        )
        parts.append(_rounded_bar(label_w, y, w, bar_h, color, f"{_esc(name)}: {_money(v)}"))
        parts.append(
            f'<text x="{label_w + w + 6}" y="{y + bar_h / 2 + 4}" font-size="12" '
            f'fill="{INK}">{_compact(v)}</text>'
        )
    return (
        f'<div class="chart-scroll"><svg width="{chart_w}" height="{height}" '
        f'viewBox="0 0 {chart_w} {height}" role="img">{"".join(parts)}</svg></div>'
    )


def _trend_svg(trend: list[dict]) -> str:
    """Monthly spend lines: contractor (blue) vs other (green)."""
    if not trend:
        return f'<p style="color:{MUTED};font-size:13px">No dated invoices in this period.</p>'
    w, h = 640, 240
    pad_l, pad_r, pad_t, pad_b = 64, 20, 14, 34
    plot_w, plot_h = w - pad_l - pad_r, h - pad_t - pad_b
    months = [m["month"] for m in trend]
    series = [
        ("Contractor", [m["contractor_spend"] for m in trend], BLUE),
        ("Other", [m["other_spend"] for m in trend], GREEN),
    ]
    max_v = max((v for _, vals, _ in series for v in vals), default=0) or 1
    n = len(months)

    def x(i: int) -> float:
        return pad_l + (plot_w * i / max(n - 1, 1) if n > 1 else plot_w / 2)

    def y(v: float) -> float:
        return pad_t + plot_h * (1 - v / max_v)

    parts: list[str] = []
    for frac in (0.0, 0.5, 1.0):  # hairline gridlines + $ ticks
        gy = pad_t + plot_h * (1 - frac)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{w - pad_r}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(
            f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="{MUTED}" style="font-variant-numeric:tabular-nums">{_compact(max_v * frac)}</text>'
        )
    step = max(1, n // 8)
    for i in range(0, n, step):
        parts.append(
            f'<text x="{x(i):.1f}" y="{h - 12}" text-anchor="middle" font-size="11" '
            f'fill="{MUTED}">{_esc(months[i])}</text>'
        )
    for label, vals, color in series:
        if not any(vals):
            continue
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for i, v in enumerate(vals):
            parts.append(
                f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4" fill="{color}" stroke="{SURFACE}" '
                f'stroke-width="2"><title>{_esc(label)} · {_esc(months[i])}: {_money(v)}</title></circle>'
            )
        parts.append(  # direct label at the line end
            f'<text x="{x(n - 1) + 8:.1f}" y="{y(vals[-1]) + 4:.1f}" font-size="11" '
            f'fill="{INK2}">{_esc(label)}</text>'
        )
    legend = "".join(
        f'<div><span class="swatch" style="background:{color}"></span>{_esc(label)}</div>'
        for label, _, color in series
    )
    return (
        f'<div class="chart-scroll"><svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="Monthly spend trend">{"".join(parts)}</svg></div>'
        f'<div class="legend">{legend}</div>'
    )


# --- page assembly ------------------------------------------------------------------------------
def report_html_bytes(aggregates: dict, narrative: str | None) -> bytes:
    t = aggregates["totals"]
    period = aggregates["period"]
    status = t.get("status_counts", {})
    matched = status.get("matched", 0)
    contractor_n = t.get("contractor_invoice_count", 0)
    matched_pct = f"{100 * matched / contractor_n:.0f}%" if contractor_n else "—"

    capex_amounts = aggregates["capex_opex"]["amounts"]
    classified = sum(capex_amounts.values())
    capex_share = (
        f"{100 * capex_amounts.get('CAPEX', 0) / classified:.0f}%" if classified else "—"
    )

    period_label = "All processed invoices"
    if period.get("start") or period.get("end"):
        period_label = f"{period.get('start') or '…'} → {period.get('end') or '…'}"

    company_rows = [
        (f"{name} (code {info['company_code']})" if info.get("company_code") else name,
         info["spend"])
        for name, info in aggregates["by_company"].items()
        if info["spend"] > 0
    ]
    vendor_rows = [(v["vendor"], v["spend"]) for v in aggregates["by_vendor"] if v["spend"] > 0]
    cost_center_rows = [(k, v) for k, v in aggregates["by_cost_center"].items() if v > 0]

    narrative_html = (
        f'<div class="card narrative">{_md_to_html(narrative)}</div>'
        if narrative
        else f'<div class="card"><p style="color:{MUTED};font-size:13px">AI narrative unavailable '
             f"(ANTHROPIC_API_KEY not configured) — figures only.</p></div>"
    )

    body = f"""
<div class="page">
  <header class="report">
    <h1>Invoice Spend Report</h1>
    <div class="sub">Upbound Group — InVoicee · Period: {_esc(period_label)} ·
      {t["invoice_count"]} invoices</div>
  </header>

  <div class="tiles">
    <div class="tile"><div class="label">Total Spend</div>
      <div class="value">{_money(t["combined_spend"])}</div>
      <div class="hint">Contractor {_compact(t["contractor_spend"])} · Other {_compact(t["other_spend"])}</div></div>
    <div class="tile"><div class="label">Invoices Processed</div>
      <div class="value">{t["invoice_count"]}</div>
      <div class="hint">{t["contractor_invoice_count"]} contractor · {t["other_invoice_count"]} other</div></div>
    <div class="tile"><div class="label">Verified (Matched)</div>
      <div class="value">{matched_pct}</div>
      <div class="hint">{matched} of {contractor_n} contractor invoices</div></div>
    <div class="tile"><div class="label">CAPEX Share</div>
      <div class="value">{capex_share}</div>
      <div class="hint">of classified spend</div></div>
  </div>

  {narrative_html}

  <div class="grid-2">
    <div class="card"><h2>CAPEX vs OPEX</h2>{_donut_svg(capex_amounts)}</div>
    <div class="card"><h2>Spend by Company</h2>{_hbar_svg(company_rows)}
      <div class="legend">Cost centers: {", ".join(_esc(f"{k} — {_compact(v)}") for k, v in cost_center_rows) or "—"}</div>
    </div>
  </div>

  <div class="card"><h2>Top Vendors</h2>{_hbar_svg(vendor_rows)}</div>

  <div class="card"><h2>Monthly Spend Trend</h2>{_trend_svg(aggregates["monthly_trend"])}</div>

  <footer class="report">Generated by InVoicee · figures aggregated from processed invoices;
    CAPEX/OPEX and company classification from Clarity/Coupa mappings.</footer>
</div>
"""
    doc = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Invoice Spend Report</title>"
        f"<style>{_CSS}</style></head><body>{body}</body></html>"
    )
    return doc.encode("utf-8")
