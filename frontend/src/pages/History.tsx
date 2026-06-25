import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { History as HistoryIcon } from "lucide-react";
import { fetchHistory, type InvoiceSummary } from "../api/client";
import { DetailDrawer } from "../components/DetailDrawer";
import { date, money, statusChip, statusLabel } from "../lib/format";

function matches(inv: InvoiceSummary, q: string): boolean {
  if (!q) return true;
  return (
    (inv.vendor_name ?? "").toLowerCase().includes(q) ||
    (inv.invoice_number ?? "").toLowerCase().includes(q) ||
    String(inv.id).includes(q)
  );
}

export function History({ search }: { search: string }) {
  const q = search.trim().toLowerCase();
  const [selected, setSelected] = useState<number | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["history"],
    queryFn: fetchHistory,
  });

  const rows = (data ?? []).filter((i) => matches(i, q));

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <span className="h-10 w-1.5 rounded-full bg-brand-lime" />
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400">Platform › History</div>
          <h1 className="text-2xl font-extrabold tracking-tight text-brand-ink">History</h1>
        </div>
      </div>

      <p className="mb-4 text-sm text-slate-500">
        Every invoice ever processed — including ones exported and cleared from the board. Use this to
        check whether an invoice was already handled. Deleted invoices are removed permanently.
      </p>

      {isLoading && <div className="text-slate-400">Loading history…</div>}
      {isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Couldn’t load history. Is the backend running on :8000?
        </div>
      )}

      {data && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2.5 font-semibold">Invoice #</th>
                <th className="px-4 py-2.5 font-semibold">Vendor</th>
                <th className="px-4 py-2.5 font-semibold">Date</th>
                <th className="px-4 py-2.5 text-right font-semibold">Total</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Stage</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-slate-400">
                    No invoices in history yet.
                  </td>
                </tr>
              )}
              {rows.map((inv) => (
                <tr
                  key={inv.id}
                  onClick={() => setSelected(inv.id)}
                  className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-500">
                    {inv.invoice_number ?? inv.id}
                  </td>
                  <td className="px-4 py-2.5 font-medium text-slate-800">
                    {inv.vendor_name ?? "Unknown vendor"}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{date(inv.date_received)}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-slate-900">
                    {money(inv.total_invoice_cost)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${statusChip[inv.status]}`}>
                      {statusLabel[inv.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    {inv.archived_at ? (
                      <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                        <HistoryIcon className="h-3 w-3" /> Exported
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium text-slate-400">On board</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected !== null && <DetailDrawer id={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
