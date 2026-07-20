import { ArrowRight, Calendar, Check, Eye } from "lucide-react";
import type { InvoiceSummary } from "../api/client";
import { date, money, parseMethodBadge, statusChip, statusLabel } from "../lib/format";

const actionIcon: Record<string, JSX.Element> = {
  matched: <Check className="h-4 w-4 text-emerald-600" />,
  flagged: <ArrowRight className="h-4 w-4 text-slate-500" />,
  needs_manual_review: <ArrowRight className="h-4 w-4 text-slate-500" />,
  processing_failed: <Eye className="h-4 w-4 text-slate-500" />,
};

// Colored left outline per status — green for matched, deep yellow for flagged.
const accentBorder: Record<string, string> = {
  matched: "border-l-emerald-500",
  flagged: "border-l-amber-500",
  needs_manual_review: "border-l-amber-500",
  processing_failed: "border-l-slate-300",
};

export function InvoiceCard({
  invoice,
  onClick,
}: {
  invoice: InvoiceSummary;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-xl border border-slate-200 border-l-4 ${accentBorder[invoice.status] ?? "border-l-slate-300"} bg-white p-4 text-left shadow-xs transition-all duration-150 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">
          #{invoice.invoice_number ?? invoice.id}
        </span>
        <span className="flex items-center gap-1">
          {(() => {
            const badge = parseMethodBadge(invoice.parse_method);
            return badge ? (
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-semibold tracking-wide ${badge.cls}`}
              >
                {badge.label}
              </span>
            ) : null;
          })()}
          <span
            className={`rounded px-2 py-0.5 text-[10px] font-semibold tracking-wide ${statusChip[invoice.status]}`}
          >
            {statusLabel[invoice.status]}
          </span>
        </span>
      </div>

      <div className="mt-2 text-base font-semibold text-slate-800">
        {invoice.vendor_name ?? "Unknown vendor"}
      </div>

      <div className="mt-1 flex items-center gap-1 text-xs text-slate-500">
        <Calendar className="h-3.5 w-3.5" />
        Due {date(invoice.date_received)}
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
        <span className="font-mono text-lg font-semibold text-slate-900">
          {money(invoice.total_invoice_cost)}
        </span>
        <span className="flex items-center gap-2 text-xs text-slate-400">
          {invoice.line_item_count > 0 && (
            <span>
              {invoice.matched_line_count}/{invoice.line_item_count}
            </span>
          )}
          {actionIcon[invoice.status]}
        </span>
      </div>
    </button>
  );
}
