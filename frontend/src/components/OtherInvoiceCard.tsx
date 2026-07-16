import { ArrowRight, Calendar, Check } from "lucide-react";
import type { OtherInvoiceSummary, OtherStatus } from "../api/client";
import { date, money } from "../lib/format";

// Visual language mirrors the contractor InvoiceCard: green = all data found, deep yellow = missing.
const statusLabel: Record<OtherStatus, string> = {
  all_data_found: "ALL DATA FOUND",
  missing_data: "MISSING DATA",
};
const statusChip: Record<OtherStatus, string> = {
  all_data_found: "bg-emerald-100 text-emerald-700",
  missing_data: "bg-amber-100 text-amber-800",
};
const accentBorder: Record<OtherStatus, string> = {
  all_data_found: "border-l-emerald-500",
  missing_data: "border-l-amber-500",
};

export function OtherInvoiceCard({
  invoice,
  onClick,
}: {
  invoice: OtherInvoiceSummary;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-xl border border-slate-700 border-l-4 ${accentBorder[invoice.status]} bg-slate-800 p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-2 hover:ring-brand-lime/40`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">
          #{invoice.invoice_number ?? invoice.id}
        </span>
        <span
          className={`rounded px-2 py-0.5 text-[10px] font-semibold tracking-wide ${statusChip[invoice.status]}`}
        >
          {statusLabel[invoice.status]}
        </span>
      </div>

      <div className="mt-2 text-base font-semibold text-slate-100">
        {invoice.vendor_name ?? "Unknown vendor"}
      </div>

      <div className="mt-1 flex items-center gap-1 text-xs text-slate-400">
        <Calendar className="h-3.5 w-3.5" />
        {date(invoice.date_received)}
      </div>

      {(invoice.budget_id || invoice.cost_center || invoice.offset_gl_account) && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-400">
          {invoice.budget_id && (
            <span>
              Budget <span className="font-mono text-slate-200">{invoice.budget_id}</span>
            </span>
          )}
          {invoice.cost_center && (
            <span>
              Cost center <span className="font-mono text-slate-200">{invoice.cost_center}</span>
            </span>
          )}
          {invoice.offset_gl_account && (
            <span>
              Offset GL <span className="font-mono text-slate-200">{invoice.offset_gl_account}</span>
            </span>
          )}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between border-t border-slate-700 pt-3">
        <span className="font-mono text-lg font-semibold text-slate-100">
          {money(invoice.total_invoice_cost)}
        </span>
        <span className="flex items-center gap-2 text-xs text-slate-400">
          {invoice.status === "missing_data" ? (
            <span className="font-medium text-amber-400">
              {invoice.missing_count} missing
            </span>
          ) : (
            <span className="font-mono text-slate-400">{invoice.supplier_number}</span>
          )}
          {invoice.status === "all_data_found" ? (
            <Check className="h-4 w-4 text-emerald-600" />
          ) : (
            <ArrowRight className="h-4 w-4 text-amber-600" />
          )}
        </span>
      </div>
    </button>
  );
}
