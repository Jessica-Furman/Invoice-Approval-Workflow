import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Download, FileBarChart, Loader2, Sparkles, X } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  downloadReportHtml,
  generateReport,
  type ReportAggregates,
  type ReportRequest,
  type ReportResponse,
} from "../api/client";
import { money } from "../lib/format";

// Validated categorical palette (blue / green / yellow pass CVD + normal-vision separation).
// Yellow is sub-3:1 on white, so every yellow mark below carries a visible direct label.
const BLUE = "#2a78d6";
const GREEN = "#008300";
const YELLOW = "#eda100";
const MUTED = "#898781";
const INK2 = "#52514e";
const GRID = "#e1e0d9";

/** Display label + color per CAPEX/OPEX bucket key from the backend. */
const CAPEX_META: Record<string, { label: string; color: string }> = {
  CAPEX: { label: "CAPEX", color: BLUE },
  OPEX: { label: "OPEX", color: GREEN },
  vendor_stated_capex: { label: "Vendor-stated CAPEX", color: YELLOW },
  vendor_stated_opex: { label: "Vendor-stated OPEX", color: YELLOW },
  unclassified: { label: "Unclassified", color: MUTED },
};

function compact(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${Math.round(n / 1_000)}K`;
  return `$${Math.round(n)}`;
}

/** Minimal Markdown renderer for the AI narrative (headings, bullets, bold — nothing else). */
function Narrative({ md }: { md: string }) {
  const blocks: JSX.Element[] = [];
  let list: string[] = [];

  const inline = (s: string) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : (
        <span key={i}>{part}</span>
      ),
    );

  const flush = () => {
    if (list.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="my-2 ml-5 list-disc space-y-1 text-sm text-slate-700">
          {list.map((li, i) => (
            <li key={i}>{inline(li)}</li>
          ))}
        </ul>,
      );
      list = [];
    }
  };

  for (const raw of md.split("\n")) {
    const line = raw.trim();
    if (!line) {
      flush();
    } else if (line.startsWith("## ")) {
      flush();
      blocks.push(
        <h3
          key={`h-${blocks.length}`}
          className="mt-5 border-t border-slate-100 pt-4 font-display text-base font-semibold text-brand-ink"
        >
          {line.slice(3)}
        </h3>,
      );
    } else if (line.startsWith("### ")) {
      flush();
      blocks.push(
        <h4 key={`h4-${blocks.length}`} className="mt-3 text-sm font-semibold text-slate-800">
          {line.slice(4)}
        </h4>,
      );
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      list.push(line.slice(2));
    } else {
      flush();
      blocks.push(
        <p key={`p-${blocks.length}`} className="my-2 text-sm leading-relaxed text-slate-700">
          {inline(line)}
        </p>,
      );
    }
  }
  flush();
  return <div>{blocks}</div>;
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 font-display text-2xl font-semibold text-brand-ink">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
      <h3 className="mb-3 text-sm font-semibold text-slate-800">{title}</h3>
      {children}
    </div>
  );
}

const tooltipStyle = {
  contentStyle: { fontSize: 12, borderRadius: 8, border: `1px solid ${GRID}` },
  formatter: (v: unknown) => (typeof v === "number" ? money(v) : String(v ?? "—")),
};

function Charts({ agg }: { agg: ReportAggregates }) {
  const capexData = Object.entries(agg.capex_opex.amounts)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      key,
      name: CAPEX_META[key]?.label ?? key,
      color: CAPEX_META[key]?.color ?? MUTED,
      value,
    }));
  const classified = capexData.reduce((a, d) => a + d.value, 0);

  const companyData = Object.entries(agg.by_company)
    .filter(([, info]) => info.spend > 0)
    .map(([name, info]) => ({
      name: info.company_code ? `${name} (${info.company_code})` : name,
      spend: info.spend,
    }));

  const vendorData = agg.by_vendor.filter((v) => v.spend > 0).slice(0, 10);
  const hasTrend = agg.monthly_trend.length > 0;

  return (
    <>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="CAPEX vs OPEX">
          {capexData.length === 0 ? (
            <p className="text-sm text-slate-400">No classified spend in this period.</p>
          ) : (
            <div className="flex flex-wrap items-center gap-4">
              <ResponsiveContainer width={190} height={190}>
                <PieChart>
                  <Pie
                    data={capexData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={82}
                    paddingAngle={2}
                    stroke="#fff"
                    strokeWidth={2}
                  >
                    {capexData.map((d) => (
                      <Cell key={d.key} fill={d.color} />
                    ))}
                  </Pie>
                  <Tooltip {...tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              {/* Direct value labels — identity never rests on color alone. */}
              <div className="flex-1 space-y-1.5 text-xs">
                {capexData.map((d) => (
                  <div key={d.key} className="flex items-center gap-2">
                    <span
                      className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                      style={{ background: d.color }}
                    />
                    <span className="text-slate-600">{d.name}</span>
                    <span className="ml-auto font-medium text-slate-900">{money(d.value)}</span>
                    <span className="w-11 text-right text-slate-400">
                      {classified ? `${((100 * d.value) / classified).toFixed(1)}%` : "—"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card title="Spend by Company">
          {companyData.length === 0 ? (
            <p className="text-sm text-slate-400">No company-attributed spend.</p>
          ) : (
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={companyData} layout="vertical" margin={{ left: 8, right: 28 }}>
                <CartesianGrid horizontal={false} stroke={GRID} />
                <XAxis type="number" tickFormatter={compact} tick={{ fontSize: 11, fill: MUTED }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  tick={{ fontSize: 11, fill: INK2 }}
                />
                <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
                <Bar dataKey="spend" fill={BLUE} radius={[0, 4, 4, 0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <Card title="Top Vendors">
        {vendorData.length === 0 ? (
          <p className="text-sm text-slate-400">No vendor spend in this period.</p>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(200, vendorData.length * 30)}>
            <BarChart data={vendorData} layout="vertical" margin={{ left: 8, right: 34 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" tickFormatter={compact} tick={{ fontSize: 11, fill: MUTED }} />
              <YAxis type="category" dataKey="vendor" width={150} tick={{ fontSize: 11, fill: INK2 }} />
              <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
              <Bar dataKey="spend" fill={BLUE} radius={[0, 4, 4, 0]} barSize={16} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card title="Monthly Spend Trend">
        {!hasTrend ? (
          <p className="text-sm text-slate-400">No dated invoices in this period.</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={agg.monthly_trend} margin={{ left: 8, right: 16 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: MUTED }} />
              <YAxis tickFormatter={compact} tick={{ fontSize: 11, fill: MUTED }} />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="contractor_spend"
                name="Contractor"
                stroke={BLUE}
                strokeWidth={2}
                dot={{ r: 4, strokeWidth: 2, stroke: "#fff" }}
              />
              <Line
                type="monotone"
                dataKey="other_spend"
                name="Other"
                stroke={GREEN}
                strokeWidth={2}
                dot={{ r: 4, strokeWidth: 2, stroke: "#fff" }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>
    </>
  );
}

export function ReportModal({ onClose }: { onClose: () => void }) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [result, setResult] = useState<ReportResponse | null>(null);

  const body = (): ReportRequest => ({
    start_date: start || null,
    end_date: end || null,
  });

  const report = useMutation({
    mutationFn: () => generateReport(body()),
    onSuccess: setResult,
  });

  const download = useMutation({ mutationFn: () => downloadReportHtml(body()) });

  // Esc closes, matching the drawer's dismissal affordances.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const agg = result?.aggregates;
  const t = agg?.totals;
  const matchedPct =
    t && t.contractor_invoice_count
      ? `${Math.round((100 * (t.status_counts.matched ?? 0)) / t.contractor_invoice_count)}%`
      : "—";
  const classified = agg ? Object.values(agg.capex_opex.amounts).reduce((a, b) => a + b, 0) : 0;
  const capexShare =
    agg && classified ? `${Math.round((100 * (agg.capex_opex.amounts.CAPEX ?? 0)) / classified)}%` : "—";

  return (
    <div
      className="fixed inset-0 z-40 flex justify-center overflow-y-auto bg-slate-900/40 p-4 sm:p-8"
      onClick={onClose}
    >
      <div
        className="h-fit w-full max-w-6xl rounded-2xl bg-brand-mist shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-3 rounded-t-2xl border-b border-slate-200 bg-white px-6 py-4">
          <FileBarChart className="h-5 w-5 text-brand-ink" strokeWidth={1.75} />
          <h2 className="font-display text-lg font-semibold tracking-tight text-brand-ink">Invoice Spend Report</h2>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-slate-500">
              From
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700"
              />
            </label>
            <label className="flex items-center gap-1.5 text-xs text-slate-500">
              To
              <input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700"
              />
            </label>
            <button
              onClick={() => report.mutate()}
              disabled={report.isPending}
              className="flex items-center gap-2 rounded-lg bg-brand-green px-4 py-2 text-sm font-semibold text-brand-ink shadow-sm transition-colors duration-150 hover:bg-brand-greenHover disabled:cursor-not-allowed disabled:opacity-70"
            >
              {report.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
              ) : (
                <Sparkles className="h-4 w-4" strokeWidth={1.75} />
              )}
              {report.isPending ? "Analyzing…" : result ? "Regenerate" : "Generate"}
            </button>
            <button onClick={onClose} className="rounded p-1 hover:bg-slate-100">
              <X className="h-5 w-5 text-slate-500" strokeWidth={1.75} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-6">
          {!result && !report.isPending && !report.isError && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
              <FileBarChart className="mx-auto h-8 w-8 text-slate-300" />
              <p className="mt-3 text-sm font-medium text-slate-700">
                Summarize every processed invoice into an executive report.
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Optionally set a date range above, then hit Generate. Spend figures are computed
                locally; AI writes the narrative only when you click.
              </p>
            </div>
          )}

          {report.isPending && (
            <div className="flex items-center gap-3 rounded-lg border border-brand-green/50 bg-brand-greenSoft/60 px-4 py-3">
              <Loader2 className="h-5 w-5 animate-spin text-brand-ink" strokeWidth={1.75} />
              <span className="text-sm font-medium text-brand-ink">
                Aggregating invoices and writing the executive summary…
              </span>
            </div>
          )}

          {report.isError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              Report generation failed. Is the backend running on :8000?
            </div>
          )}

          {result && agg && t && (
            <>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Tile
                  label="Total Spend"
                  value={money(t.combined_spend)}
                  hint={`Contractor ${compact(t.contractor_spend)} · Other ${compact(t.other_spend)}`}
                />
                <Tile
                  label="Invoices"
                  value={String(t.invoice_count)}
                  hint={`${t.contractor_invoice_count} contractor · ${t.other_invoice_count} other`}
                />
                <Tile
                  label="Verified"
                  value={matchedPct}
                  hint={`${t.status_counts.matched ?? 0} of ${t.contractor_invoice_count} matched`}
                />
                <Tile label="CAPEX Share" value={capexShare} hint="of classified spend" />
              </div>

              {result.narrative ? (
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                  <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-brand-ink">
                    <Sparkles className="h-3.5 w-3.5 text-brand-greenHover" strokeWidth={1.75} />
                    AI Executive Summary
                  </div>
                  <Narrative md={result.narrative} />
                </div>
              ) : (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                  Figures only — add <code className="font-mono">ANTHROPIC_API_KEY</code> to your{" "}
                  <code className="font-mono">.env</code> and restart the backend to get the AI
                  executive summary.
                </div>
              )}

              <Charts agg={agg} />

              <div className="flex items-center justify-between border-t border-slate-200 pt-4">
                <span className="text-xs text-slate-400">
                  {agg.period.generated_from_invoices} invoices ·{" "}
                  {agg.period.start ?? "all time"} → {agg.period.end ?? "now"}
                </span>
                <button
                  onClick={() => download.mutate()}
                  disabled={download.isPending}
                  className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-70"
                >
                  {download.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  Download HTML
                </button>
              </div>
              {download.isError && (
                <p className="text-right text-xs text-rose-600">Download failed.</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
