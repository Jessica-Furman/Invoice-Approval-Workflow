import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, FolderOpen, Loader2, Plus } from "lucide-react";
import {
  fetchOtherDashboard,
  uploadOtherInvoices,
  type OtherInvoiceSummary,
  type UploadResult,
} from "../api/client";
import { OtherInvoiceCard } from "../components/OtherInvoiceCard";
import { OtherDetailDrawer } from "../components/OtherDetailDrawer";

export type OtherView = "dashboard" | "missing" | "found" | "all" | "history";

const TITLES: Record<OtherView, string> = {
  dashboard: "Other Invoices",
  missing: "Missing Data",
  found: "All Data Found",
  all: "All Other Invoices",
  history: "Other History",
};

type ColumnKind = "missing" | "found" | "all";
const COLUMN_CFG: Record<ColumnKind, { label: string; icon: typeof FolderOpen; text: string; iconClass: string }> = {
  missing: { label: "Missing Data", icon: AlertCircle, text: "text-amber-400", iconClass: "h-4 w-4 text-amber-400" },
  found: { label: "All Data Found", icon: CheckCircle2, text: "text-emerald-400", iconClass: "h-4 w-4 text-emerald-400" },
  all: { label: "All", icon: FolderOpen, text: "text-slate-300", iconClass: "h-4 w-4 text-slate-400" },
};

function OtherColumn({
  kind,
  invoices,
  onSelect,
}: {
  kind: ColumnKind;
  invoices: OtherInvoiceSummary[];
  onSelect: (id: number) => void;
}) {
  const cfg = COLUMN_CFG[kind];
  const Icon = cfg.icon;
  return (
    <div className="flex-1 min-w-[280px]">
      <div className="mb-3 flex h-10 items-center gap-2">
        <Icon className={cfg.iconClass} />
        <h2 className={`text-sm font-bold uppercase tracking-wide ${cfg.text}`}>{cfg.label}</h2>
        <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-slate-300">
          {invoices.length}
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {invoices.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-xs text-slate-500">
            No invoices
          </div>
        )}
        {invoices.map((inv) => (
          <OtherInvoiceCard key={inv.id} invoice={inv} onClick={() => onSelect(inv.id)} />
        ))}
      </div>
    </div>
  );
}

function matchesSearch(inv: OtherInvoiceSummary, q: string): boolean {
  if (!q) return true;
  return (
    (inv.vendor_name ?? "").toLowerCase().includes(q) ||
    (inv.invoice_number ?? "").toLowerCase().includes(q) ||
    String(inv.id).includes(q)
  );
}

const PROCESSING_MESSAGES = ["Upload in progress…", "Parsing data…", "Processing data…"];

function ProcessingIndicator() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((n) => (n + 1) % PROCESSING_MESSAGES.length), 1400);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="mb-4 flex items-center gap-3 rounded-lg border border-brand-lime bg-lime-50 px-4 py-3">
      <Loader2 className="h-5 w-5 animate-spin text-brand-limedark" />
      <span className="text-sm font-medium text-brand-ink">{PROCESSING_MESSAGES[i]}</span>
    </div>
  );
}

export function OtherDashboard({ view, search }: { view: OtherView; search: string }) {
  const q = search.trim().toLowerCase();
  const [selected, setSelected] = useState<number | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["other-dashboard"],
    queryFn: fetchOtherDashboard,
  });

  const upload = useMutation({
    mutationFn: uploadOtherInvoices,
    onSuccess: (result) => {
      setUploadResult(result);
      queryClient.invalidateQueries({ queryKey: ["other-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["other-history"] });
    },
  });

  function onFilesChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length) {
      setUploadResult(null);
      upload.mutate(files);
    }
    e.target.value = "";
  }

  const filt = (rows: OtherInvoiceSummary[]) => rows.filter((i) => matchesSearch(i, q));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="h-10 w-1.5 rounded-full bg-brand-lime" />
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-400">Platform › {TITLES[view]}</div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100">{TITLES[view]}</h1>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="hidden"
          onChange={onFilesChosen}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={upload.isPending}
          className="flex items-center gap-2 rounded-lg bg-brand-lime px-5 py-2.5 text-sm font-bold text-brand-inkdark shadow-[0_4px_14px_rgba(164,214,30,0.45)] transition hover:bg-brand-limeglow hover:shadow-[0_4px_20px_rgba(164,214,30,0.6)] disabled:cursor-not-allowed disabled:opacity-70"
        >
          {upload.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          {upload.isPending ? "Working…" : "Upload Invoice"}
        </button>
      </div>

      {upload.isPending && <ProcessingIndicator />}
      {upload.isError && (
        <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Upload failed. Is the backend running on :8000?
        </div>
      )}
      {uploadResult && (
        <div className="mb-4 rounded-lg border border-slate-700 bg-slate-800 p-4 text-sm text-slate-300">
          Uploaded <span className="font-semibold text-emerald-400">{uploadResult.uploaded}</span>
          {uploadResult.failed > 0 && (
            <>, <span className="text-rose-400">{uploadResult.failed} failed</span></>
          )}
          .
        </div>
      )}

      {isLoading && <div className="text-slate-400">Loading invoices…</div>}
      {isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Couldn’t reach the API. Is the backend running on :8000?
        </div>
      )}

      {data && (
        <div className="flex flex-wrap gap-6">
          {(view === "dashboard" || view === "missing") && (
            <OtherColumn kind="missing" invoices={filt(data.missing)} onSelect={setSelected} />
          )}
          {(view === "dashboard" || view === "found") && (
            <OtherColumn kind="found" invoices={filt(data.found)} onSelect={setSelected} />
          )}
          {(view === "dashboard" || view === "all") && (
            <OtherColumn kind="all" invoices={filt(data.all)} onSelect={setSelected} />
          )}
        </div>
      )}

      {selected !== null && <OtherDetailDrawer id={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
