import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, FileText, X } from "lucide-react";
import {
  fetchInvoice,
  type ClarityProject,
  type ClarityTimesheet,
  type LineItem,
} from "../api/client";
import { date, money, statusChip, statusLabel } from "../lib/format";

function sum(nums: (number | null)[]): number {
  return nums.reduce((acc: number, n) => acc + (n ?? 0), 0);
}

function InvoiceTable({ items }: { items: LineItem[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
          <th className="py-2 font-medium">Name</th>
          <th className="py-2 font-medium">Hours</th>
          <th className="py-2 font-medium">Rate</th>
          <th className="py-2 text-right font-medium">Amount</th>
        </tr>
      </thead>
      <tbody>
        {items.map((li) => {
          const bad = li.line_status && li.line_status !== "matched";
          return (
            <tr
              key={li.id}
              className={`border-b border-slate-100 ${bad ? "bg-rose-50" : ""}`}
            >
              <td className="py-2 text-slate-700">{li.contractor_name}</td>
              <td className="py-2 text-slate-600">{li.hours ?? "—"}</td>
              <td className="py-2 text-slate-600">{li.rate ?? "—"}</td>
              <td className="py-2 text-right font-mono text-slate-800">{money(li.amount)}</td>
            </tr>
          );
        })}
        <tr className="font-semibold">
          <td className="py-2">Total</td>
          <td />
          <td />
          <td className="py-2 text-right font-mono">{money(sum(items.map((i) => i.amount)))}</td>
        </tr>
      </tbody>
    </table>
  );
}

function ClarityTable({ rows }: { rows: ClarityTimesheet[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
          <th className="py-2 font-medium">Name</th>
          <th className="py-2 font-medium">Hours</th>
          <th className="py-2 font-medium">Rate</th>
          <th className="py-2 text-right font-medium">Amount</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((t) => {
          const amount = (t.hours ?? 0) * (t.rate ?? 0);
          return (
            <tr key={t.id} className="border-b border-slate-100">
              <td className="py-2 text-slate-700">{t.contractor_name}</td>
              <td className="py-2 text-slate-600">{t.hours ?? "—"}</td>
              <td className="py-2 text-slate-600">{t.rate ?? "—"}</td>
              <td className="py-2 text-right font-mono text-slate-800">{money(amount)}</td>
            </tr>
          );
        })}
        <tr className="font-semibold">
          <td className="py-2">Total</td>
          <td />
          <td />
          <td className="py-2 text-right font-mono">
            {money(sum(rows.map((t) => (t.hours ?? 0) * (t.rate ?? 0))))}
          </td>
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
          <th className="py-2 font-medium">Vendor</th>
          <th className="py-2 font-medium">LOB</th>
          <th className="py-2 font-medium">Cost Center</th>
          <th className="py-2 font-medium">Project</th>
          <th className="py-2 text-right font-medium">Spend</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr key={p.id} className="border-b border-slate-100">
            <td className="py-2 text-slate-700">{p.capex_opex}</td>
            <td className="py-2 text-slate-600">{p.vendor}</td>
            <td className="py-2 text-slate-600">{p.lob}</td>
            <td className="py-2 text-slate-600">{p.cost_center}</td>
            <td className="py-2 text-slate-600">{p.project_name}</td>
            <td className="py-2 text-right font-mono text-slate-800">{money(p.spend)}</td>
          </tr>
        ))}
        <tr className="font-semibold">
          <td className="py-2">Total</td>
          <td colSpan={4} />
          <td className="py-2 text-right font-mono">{money(sum(rows.map((p) => p.spend)))}</td>
        </tr>
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
                <span
                  className={`rounded px-2 py-1 text-xs font-semibold ${statusChip[data.status]}`}
                >
                  {statusLabel[data.status]}
                </span>
                <button onClick={onClose} className="rounded p-1 hover:bg-slate-100">
                  <X className="h-5 w-5 text-slate-500" />
                </button>
              </div>
            </div>

            {/* Mismatch reasons */}
            {data.mismatch_reasons.length > 0 && (
              <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 p-4">
                <h3 className="mb-2 text-sm font-semibold text-rose-700">
                  What didn’t match
                </h3>
                <ul className="space-y-1 text-sm text-rose-700">
                  {data.mismatch_reasons.map((m, i) => (
                    <li key={i}>
                      <span className="font-medium capitalize">{m.field}:</span> {m.reason}{" "}
                      {m.invoice_value || m.clarity_value ? (
                        <span className="text-rose-500">
                          (invoice {m.invoice_value ?? "—"} vs Clarity {m.clarity_value ?? "—"})
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Side-by-side */}
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-800">Invoice Data</h3>
                  <span className="text-sm text-slate-500">
                    Match: {data.matched_line_count}/{data.line_item_count}
                  </span>
                </div>
                <InvoiceTable items={data.line_items} />
                <div className="mt-4 space-y-1 text-sm text-slate-600">
                  <div>Vendor: {data.vendor_name}</div>
                  <div>Invoice #: {data.invoice_number}</div>
                  <div>
                    Time Period: {date(data.payment_period_start)} –{" "}
                    {date(data.payment_period_end)}
                  </div>
                  {data.pdf_storage_key && (
                    <div className="flex items-center gap-1 text-blue-600">
                      <FileText className="h-4 w-4" />
                      {data.pdf_storage_key}
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-lg font-semibold text-slate-800">Clarity Data</h3>
                <ClarityTable rows={data.clarity_timesheets} />
              </div>
            </div>

            {/* Projects */}
            <div className="mt-10">
              <h3 className="mb-2 text-lg font-semibold text-slate-800">
                Clarity Project Details
              </h3>
              <ProjectTable rows={data.clarity_projects} />
            </div>

            {/* Actions (wired in later milestones) */}
            <div className="mt-8 flex justify-end gap-3">
              <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Export to Excel
              </button>
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
