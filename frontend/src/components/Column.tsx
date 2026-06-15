import type { InvoiceSummary } from "../api/client";
import { InvoiceCard } from "./InvoiceCard";

export function Column({
  title,
  dotClass,
  invoices,
  onSelect,
}: {
  title: string;
  dotClass: string;
  invoices: InvoiceSummary[];
  onSelect: (id: number) => void;
}) {
  return (
    <div className="flex-1 min-w-[280px]">
      <div className="mb-3 flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${dotClass}`} />
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {title}
        </h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
          {invoices.length}
        </span>
      </div>

      <div className="flex flex-col gap-3">
        {invoices.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-xs text-slate-400">
            No invoices
          </div>
        )}
        {invoices.map((inv) => (
          <InvoiceCard key={inv.id} invoice={inv} onClick={() => onSelect(inv.id)} />
        ))}
      </div>
    </div>
  );
}
