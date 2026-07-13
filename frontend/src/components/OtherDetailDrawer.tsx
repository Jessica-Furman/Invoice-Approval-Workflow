import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, FileText, Trash2, X } from "lucide-react";
import {
  deleteInvoice,
  fetchOtherInvoice,
  invoicePdfUrl,
  type OtherStatus,
} from "../api/client";
import { date, money } from "../lib/format";

const statusLabel: Record<OtherStatus, string> = {
  all_data_found: "ALL DATA FOUND",
  missing_data: "MISSING DATA",
};
const statusChip: Record<OtherStatus, string> = {
  all_data_found: "bg-emerald-100 text-emerald-700",
  missing_data: "bg-amber-100 text-amber-800",
};

function num(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return Number.isInteger(n) ? String(n) : String(n);
}

/** A labeled field in the summary grid. */
function Field({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm text-slate-100 ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}

export function OtherDetailDrawer({ id, onClose }: { id: number; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["other-invoice", id],
    queryFn: () => fetchOtherInvoice(id),
  });

  const del = useMutation({
    mutationFn: () => deleteInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["other-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["other-history"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-slate-900/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-3xl overflow-y-auto bg-slate-900 shadow-2xl"
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
                className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100"
              >
                <ArrowLeft className="h-4 w-4" />
                {data.invoice_number ?? `#${data.id}`} — {date(data.date_received)}
              </button>
              <div className="flex items-center gap-3">
                <span className={`rounded px-2 py-1 text-xs font-semibold ${statusChip[data.status]}`}>
                  {statusLabel[data.status]}
                </span>
                <button onClick={onClose} className="rounded p-1 hover:bg-slate-800">
                  <X className="h-5 w-5 text-slate-400" />
                </button>
              </div>
            </div>

            {/* Vendor + total headline */}
            <div className="mb-6 flex items-end justify-between border-b border-slate-800 pb-5">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Vendor</div>
                <div className="text-2xl font-bold text-slate-100">{data.vendor_name ?? "Unknown vendor"}</div>
              </div>
              <div className="text-right">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Total</div>
                <div className="font-mono text-2xl font-bold text-slate-100">{money(data.total_invoice_cost)}</div>
              </div>
            </div>

            {/* Summary fields */}
            <div className="mb-6 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
              <Field label="Supplier #" value={data.supplier_number ?? "—"} mono />
              <Field label="Invoice #" value={data.invoice_number ?? "—"} mono />
              <Field label="Date Received" value={date(data.date_received)} />
              <Field label="Line Items" value={data.line_item_count} />
              <Field label="Cost Center" value={data.cost_center ?? "—"} mono />
              <Field label="Offset GL Account" value={data.offset_gl_account ?? "—"} mono />
            </div>

            {/* Missing-data banner */}
            {data.status === "missing_data" && data.missing_fields.length > 0 && (
              <div className="mb-6 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                <div className="text-sm text-amber-200">
                  <span className="font-semibold">Missing data:</span>{" "}
                  {data.missing_fields.join(", ")}. The rest of the fields were parsed successfully.
                </div>
              </div>
            )}

            {/* Line-item table */}
            <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-400">Service Lines</h3>
            <div className="overflow-hidden rounded-lg border border-slate-700">
              <table className="w-full text-sm">
                <thead className="bg-slate-800 text-left text-[11px] uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Description</th>
                    <th className="px-3 py-2 text-right font-semibold">Qty</th>
                    <th className="px-3 py-2 text-right font-semibold">Unit Price</th>
                    <th className="px-3 py-2 text-right font-semibold">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {data.line_items.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-3 py-4 text-center text-slate-500">
                        No service lines were parsed.
                      </td>
                    </tr>
                  )}
                  {data.line_items.map((li) => (
                    <tr key={li.id} className="border-t border-slate-800">
                      <td className="px-3 py-2 text-slate-200">{li.description ?? "—"}</td>
                      <td className="px-3 py-2 text-right text-slate-400">
                        {li.quantity === null ? "—" : num(li.quantity)}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-400">
                        {li.unit_price === null ? "—" : money(li.unit_price)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-slate-100">{money(li.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Actions */}
            <div className="mt-8 flex items-center justify-between gap-3">
              {confirmingDelete ? (
                <div className="flex items-center gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2">
                  <span className="text-sm text-rose-300">Delete this invoice? This can’t be undone.</span>
                  <button
                    onClick={() => del.mutate()}
                    disabled={del.isPending}
                    className="rounded-lg bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-500 disabled:opacity-60"
                  >
                    {del.isPending ? "Deleting…" : "Yes, delete"}
                  </button>
                  <button
                    onClick={() => setConfirmingDelete(false)}
                    disabled={del.isPending}
                    className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmingDelete(true)}
                  className="flex items-center gap-1.5 rounded-lg border border-rose-500/40 px-4 py-2 text-sm font-medium text-rose-400 hover:bg-rose-500/10"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete Invoice
                </button>
              )}

              {data.pdf_storage_key && (
                <a
                  href={invoicePdfUrl(data.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
                >
                  <FileText className="h-4 w-4" />
                  Open PDF
                </a>
              )}
            </div>
            {del.isError && (
              <div className="mt-3 text-right text-sm text-rose-400">
                Couldn’t delete the invoice. Is the backend running?
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
