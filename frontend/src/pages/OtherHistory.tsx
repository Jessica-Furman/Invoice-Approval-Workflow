import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchOtherHistory, type OtherInvoiceSummary, type OtherStatus } from "../api/client";
import { OtherDetailDrawer } from "../components/OtherDetailDrawer";
import { date, money } from "../lib/format";

const statusLabel: Record<OtherStatus, string> = {
  all_data_found: "ALL DATA FOUND",
  missing_data: "MISSING DATA",
};
const statusChip: Record<OtherStatus, string> = {
  all_data_found: "bg-brand-green/15 text-brand-green",
  missing_data: "bg-amber-400/15 text-amber-400",
};

function matches(inv: OtherInvoiceSummary, q: string): boolean {
  if (!q) return true;
  return (
    (inv.vendor_name ?? "").toLowerCase().includes(q) ||
    (inv.invoice_number ?? "").toLowerCase().includes(q) ||
    String(inv.id).includes(q)
  );
}

export function OtherHistory({ search }: { search: string }) {
  const q = search.trim().toLowerCase();
  const [selected, setSelected] = useState<number | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["other-history"],
    queryFn: fetchOtherHistory,
  });

  const rows = (data ?? []).filter((i) => matches(i, q));

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <span className="h-9 w-1.5 rounded-full bg-brand-green" />
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-white/40">Platform › Other History</div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">Other Invoice History</h1>
        </div>
      </div>

      <p className="mb-4 text-sm text-white/50">
        Every hardware / software / subscription invoice processed. Separate from the contractor
        History. Deleted invoices are removed permanently.
      </p>

      {isLoading && <div className="text-white/40">Loading history…</div>}
      {isError && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          Couldn’t load history. Is the backend running on :8000?
        </div>
      )}

      {data && (
        <div className="overflow-hidden rounded-xl border border-white/10 bg-brand-charcoal">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.04] text-left text-xs uppercase tracking-wide text-white/40">
                <th className="px-4 py-2.5 font-semibold">Invoice #</th>
                <th className="px-4 py-2.5 font-semibold">Vendor</th>
                <th className="px-4 py-2.5 font-semibold">Supplier #</th>
                <th className="px-4 py-2.5 font-semibold">Date</th>
                <th className="px-4 py-2.5 text-right font-semibold">Total</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-white/40">
                    No other invoices in history yet.
                  </td>
                </tr>
              )}
              {rows.map((inv) => (
                <tr
                  key={inv.id}
                  onClick={() => setSelected(inv.id)}
                  className="cursor-pointer border-b border-white/10 hover:bg-white/[0.05]"
                >
                  <td className="px-4 py-2.5 font-mono text-xs text-white/40">
                    {inv.invoice_number ?? inv.id}
                  </td>
                  <td className="px-4 py-2.5 font-medium text-white">
                    {inv.vendor_name ?? "Unknown vendor"}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-white/40">
                    {inv.supplier_number ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-white/60">{date(inv.date_received)}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-white">
                    {money(inv.total_invoice_cost)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${statusChip[inv.status]}`}>
                      {statusLabel[inv.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected !== null && <OtherDetailDrawer id={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
