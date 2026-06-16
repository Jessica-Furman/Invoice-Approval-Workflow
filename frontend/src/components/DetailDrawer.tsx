import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, ChevronRight, FileText, X } from "lucide-react";
import {
  fetchClarityEntries,
  fetchInvoice,
  invoiceExcelUrl,
  invoicePdfUrl,
  type ClarityProject,
  type InvoiceDetail as InvoiceDetailT,
  type LineItem,
} from "../api/client";
import { date, money, statusChip, statusLabel } from "../lib/format";

function sum(nums: (number | null | undefined)[]): number {
  return nums.reduce((acc: number, n) => acc + (n ?? 0), 0);
}

function num(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}
function str(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}

/** Date-level breakdown shown when a Clarity contractor row is expanded. */
function ClarityBreakdown({ invoiceId, lineId }: { invoiceId: number; lineId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["clarity-entries", invoiceId, lineId],
    queryFn: () => fetchClarityEntries(invoiceId, lineId),
  });

  if (isLoading) return <div className="px-4 py-3 text-xs text-slate-400">Loading entries…</div>;
  if (!data || data.length === 0)
    return <div className="px-4 py-3 text-xs text-slate-400">No Clarity entries in this period.</div>;

  const included = data.filter((e) => e.included);
  return (
    <div className="bg-slate-50 px-4 py-3">
      <div className="mb-2 text-xs font-medium text-slate-500">
        How this total was summed — {included.length} counted of {data.length} entries in period
        (time-off & non-posted excluded)
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-slate-400">
            <th className="py-1 font-medium">Date Worked</th>
            <th className="py-1 font-medium">Project</th>
            <th className="py-1 font-medium">Task</th>
            <th className="py-1 font-medium">Status</th>
            <th className="py-1 text-right font-medium">Hours</th>
          </tr>
        </thead>
        <tbody>
          {data.map((e) => (
            <tr
              key={e.id}
              className={`border-t border-slate-200 ${e.included ? "" : "text-slate-400 line-through"}`}
            >
              <td className="py-1">{date(e.date_worked)}</td>
              <td className="py-1">{e.investment_name ?? e.project_id ?? "—"}</td>
              <td className="py-1">{e.task_name ?? "—"}</td>
              <td className="py-1">
                {e.is_time_off ? "Time off" : !e.is_posted ? e.task_name && "Not posted" : "Posted"}
                {!e.included && (
                  <span className="ml-1 rounded bg-slate-200 px-1 text-[10px] text-slate-600 no-underline">
                    excluded
                  </span>
                )}
              </td>
              <td className="py-1 text-right font-mono">{e.hours ?? "—"}</td>
            </tr>
          ))}
          <tr className="border-t border-slate-300 font-semibold">
            <td className="py-1" colSpan={4}>
              Counted total
            </td>
            <td className="py-1 text-right font-mono">{sum(included.map((e) => e.hours))}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/** A single aligned comparison row: invoice line on the left, matched Clarity on the right. */
function ComparisonRow({
  invoiceId,
  li,
}: {
  invoiceId: number;
  li: LineItem;
}) {
  const [open, setOpen] = useState(false);
  const diff = li.diff ?? {};
  const clarityName = str(diff["clarity_name"]);
  const clarityHours = num(diff["clarity_hours"]);
  const delta = num(diff["hours_delta"]);
  const resolved = str(diff["match_method"]) && str(diff["match_method"]) !== "unresolved";
  const bad = li.line_status && li.line_status !== "matched";

  return (
    <>
      <tr className={`border-b border-slate-100 ${bad ? "bg-rose-50" : ""}`}>
        {/* Invoice side */}
        <td className="py-2 pl-1 text-slate-700">{li.contractor_name}</td>
        <td className="py-2 text-right text-slate-600">{li.hours ?? "—"}</td>
        <td className="py-2 text-right text-slate-500">{li.rate ?? "—"}</td>
        <td className="py-2 text-right font-mono text-slate-800">{money(li.amount)}</td>
        {/* divider */}
        <td className="w-px bg-slate-200 p-0" />
        {/* Clarity side */}
        <td className="py-2 pl-3">
          {resolved ? (
            <button
              onClick={() => setOpen((o) => !o)}
              className="flex items-center gap-1 text-left text-slate-700 hover:text-blue-700"
            >
              {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              {clarityName ?? li.contractor_name}
            </button>
          ) : (
            <span className="text-rose-500">no match</span>
          )}
        </td>
        <td className="py-2 text-right text-slate-600">{clarityHours ?? "—"}</td>
        <td
          className={`py-2 pr-1 text-right font-mono ${
            delta && Math.abs(delta) > 0.001 ? "text-rose-600" : "text-slate-400"
          }`}
        >
          {delta === null ? "—" : delta > 0 ? `+${delta}` : delta}
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} className="p-0">
            <ClarityBreakdown invoiceId={invoiceId} lineId={li.id} />
          </td>
        </tr>
      )}
    </>
  );
}

function ComparisonTable({ data }: { data: InvoiceDetailT }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
          <th className="pb-1" colSpan={4}>
            Invoice Data
          </th>
          <th className="pb-1" />
          <th className="pb-1" colSpan={3}>
            Clarity Data
          </th>
        </tr>
        <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
          <th className="py-2 pl-1 font-medium">Contractor</th>
          <th className="py-2 text-right font-medium">Hours</th>
          <th className="py-2 text-right font-medium">Rate</th>
          <th className="py-2 text-right font-medium">Amount</th>
          <th className="p-0" />
          <th className="py-2 pl-3 font-medium">Contractor</th>
          <th className="py-2 text-right font-medium">Hours</th>
          <th className="py-2 pr-1 text-right font-medium">Δ</th>
        </tr>
      </thead>
      <tbody>
        {data.line_items.map((li) => (
          <ComparisonRow key={li.id} invoiceId={data.id} li={li} />
        ))}
        <tr className="font-semibold">
          <td className="py-2 pl-1">Total</td>
          <td className="py-2 text-right">{sum(data.line_items.map((l) => l.hours))}</td>
          <td />
          <td className="py-2 text-right font-mono">{money(sum(data.line_items.map((l) => l.amount)))}</td>
          <td className="p-0" />
          <td className="py-2 pl-3" />
          <td className="py-2 text-right">
            {sum(data.line_items.map((l) => num((l.diff ?? {})["clarity_hours"])))}
          </td>
          <td />
        </tr>
      </tbody>
    </table>
  );
}

function ProjectTable({ rows }: { rows: ClarityProject[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
          <th className="py-2 font-medium">Type</th>
          <th className="py-2 font-medium">Project</th>
          <th className="py-2 font-medium">Budget ID</th>
          <th className="py-2 font-medium">Cost Center</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr key={p.id} className="border-b border-slate-100">
            <td className="py-2 text-slate-700">{p.capex_opex ?? "—"}</td>
            <td className="py-2 text-slate-600">{p.project_name ?? p.project_id}</td>
            <td className="py-2 text-slate-600">{p.budget_id ?? "—"}</td>
            <td className="py-2 text-slate-600">{p.cost_center ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function DetailDrawer({ id, onClose }: { id: number; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => fetchInvoice(id),
  });

  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-slate-900/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {isLoading || !data ? (
          <div className="p-10 text-slate-400">Loading…</div>
        ) : (
          <div className="p-6">
            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
              <button
                onClick={onClose}
                className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800"
              >
                <ArrowLeft className="h-4 w-4" />
                {data.invoice_number} — {date(data.date_received)}
              </button>
              <div className="flex items-center gap-3">
                <span className={`rounded px-2 py-1 text-xs font-semibold ${statusChip[data.status]}`}>
                  {statusLabel[data.status]}
                </span>
                <button onClick={onClose} className="rounded p-1 hover:bg-slate-100">
                  <X className="h-5 w-5 text-slate-500" />
                </button>
              </div>
            </div>

            {/* Meta */}
            <div className="mb-4 flex flex-wrap gap-x-8 gap-y-1 text-sm text-slate-600">
              <span>Vendor: <span className="font-medium text-slate-800">{data.vendor_name}</span></span>
              <span>
                Period: {date(data.payment_period_start)} – {date(data.payment_period_end)}
              </span>
              <span>
                Match: {data.matched_line_count}/{data.line_item_count}
              </span>
              {data.routed_to && (
                <span>
                  Routed to: <span className="font-medium capitalize text-slate-800">{data.routed_to}</span> inbox
                </span>
              )}
              {data.pdf_storage_key && (
                <a
                  href={invoicePdfUrl(data.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-blue-600 hover:underline"
                >
                  <FileText className="h-4 w-4" />
                  {data.pdf_storage_key}
                </a>
              )}
            </div>

            {/* Mismatch reasons */}
            {data.mismatch_reasons.length > 0 && (
              <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 p-4">
                <h3 className="mb-2 text-sm font-semibold text-rose-700">What didn’t match</h3>
                <ul className="space-y-1 text-sm text-rose-700">
                  {data.mismatch_reasons.map((m, i) => (
                    <li key={i}>
                      <span className="font-medium capitalize">{m.field}:</span> {m.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Aligned comparison */}
            <div className="mb-2 text-xs text-slate-400">
              Tip: click a contractor under Clarity Data to see the date-level breakdown.
            </div>
            <ComparisonTable data={data} />

            {/* Projects */}
            <div className="mt-10">
              <h3 className="mb-2 text-lg font-semibold text-slate-800">Clarity Project Details</h3>
              {data.clarity_projects.length > 0 ? (
                <ProjectTable rows={data.clarity_projects} />
              ) : (
                <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">
                  No linked Clarity projects.
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="mt-8 flex justify-end gap-3">
              <a
                href={invoiceExcelUrl(data.id)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
              >
                Export to Excel
              </a>
              {data.status === "matched" ? (
                <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  Approved, create CSV
                </button>
              ) : (
                <button className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900">
                  Mark as Matched
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
