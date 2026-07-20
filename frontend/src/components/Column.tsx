import { useMemo, useState } from "react";
import { ArrowDownUp, Check, CheckCircle2, Flag, FolderOpen } from "lucide-react";
import type { InvoiceSummary } from "../api/client";
import { InvoiceCard } from "./InvoiceCard";

export type ColumnVariant = "flagged" | "matched" | "all";

/** Per-column header: just an icon + bold colored label (no box). */
const VARIANTS: Record<
  ColumnVariant,
  { label: string; icon: typeof Flag; text: string; iconClass: string }
> = {
  flagged: {
    label: "Flagged",
    icon: Flag,
    text: "text-amber-700",
    iconClass: "h-4 w-4 fill-amber-500 text-amber-700",
  },
  matched: {
    label: "Matched",
    icon: CheckCircle2,
    text: "text-emerald-600",
    iconClass: "h-4 w-4 text-emerald-600",
  },
  all: {
    label: "All",
    icon: FolderOpen,
    text: "text-slate-500",
    iconClass: "h-4 w-4 text-slate-500",
  },
};

type SortKey =
  | "default"
  | "price_desc"
  | "price_asc"
  | "date_desc"
  | "date_asc";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "default", label: "Default order" },
  { key: "price_desc", label: "Price: high → low" },
  { key: "price_asc", label: "Price: low → high" },
  { key: "date_desc", label: "Date: newest first" },
  { key: "date_asc", label: "Date: oldest first" },
];

function sortInvoices(invoices: InvoiceSummary[], key: SortKey): InvoiceSummary[] {
  if (key === "default") return invoices;
  const copy = [...invoices];
  const price = (i: InvoiceSummary) => i.total_invoice_cost ?? 0;
  const time = (i: InvoiceSummary) =>
    i.date_received ? new Date(i.date_received + "T00:00:00").getTime() : 0;
  switch (key) {
    case "price_desc":
      return copy.sort((a, b) => price(b) - price(a));
    case "price_asc":
      return copy.sort((a, b) => price(a) - price(b));
    case "date_desc":
      return copy.sort((a, b) => time(b) - time(a));
    case "date_asc":
      return copy.sort((a, b) => time(a) - time(b));
    default:
      return copy;
  }
}

function SortMenu({ value, onChange }: { value: SortKey; onChange: (k: SortKey) => void }) {
  const [open, setOpen] = useState(false);
  const active = value !== "default";
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium transition-colors duration-150 ${
          active ? "border-brand-green/60 bg-brand-greenSoft/60 text-brand-ink" : "border-slate-200 text-slate-500 hover:bg-slate-50"
        }`}
      >
        <ArrowDownUp className="h-3.5 w-3.5" strokeWidth={1.75} />
        Sort
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-48 rounded-lg border border-slate-200 bg-white py-1 shadow-md">
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => {
                  onChange(opt.key);
                  setOpen(false);
                }}
                className="flex w-full items-center justify-between px-3 py-1.5 text-left text-xs text-slate-600 hover:bg-slate-50"
              >
                {opt.label}
                {value === opt.key && <Check className="h-3.5 w-3.5 text-brand-ink" strokeWidth={1.75} />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export function Column({
  variant,
  invoices,
  onSelect,
  headerExtra,
}: {
  variant: ColumnVariant;
  invoices: InvoiceSummary[];
  onSelect: (id: number) => void;
  headerExtra?: React.ReactNode;
}) {
  const [sort, setSort] = useState<SortKey>("default");
  const sorted = useMemo(() => sortInvoices(invoices, sort), [invoices, sort]);
  const cfg = VARIANTS[variant];
  const Icon = cfg.icon;

  return (
    <div className="flex-1 min-w-[280px]">
      {/* Fixed height (matches the SlideToExport bar) so all columns' card lists start level,
          whether or not a column has a headerExtra control. */}
      <div className="mb-3 flex h-10 items-center gap-2">
        <Icon className={cfg.iconClass} />
        <h2 className={`text-sm font-bold uppercase tracking-wide ${cfg.text}`}>{cfg.label}</h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-500">
          {invoices.length}
        </span>
        {/* Slider (Matched column) sits to the right of the label, filling the row. */}
        {headerExtra && <div className="ml-2 min-w-[160px] flex-1">{headerExtra}</div>}
        <div className={headerExtra ? "" : "ml-auto"}>
          <SortMenu value={sort} onChange={setSort} />
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {sorted.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-xs text-slate-400">
            No invoices
          </div>
        )}
        {sorted.map((inv) => (
          <InvoiceCard key={inv.id} invoice={inv} onClick={() => onSelect(inv.id)} />
        ))}
      </div>
    </div>
  );
}
