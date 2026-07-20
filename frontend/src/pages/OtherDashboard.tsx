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
  found: { label: "All Data Found", icon: CheckCircle2, text: "text-brand-green", iconClass: "h-4 w-4 text-brand-green" },
  all: { label: "All", icon: FolderOpen, text: "text-white/60", iconClass: "h-4 w-4 text-white/50" },
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
        <Icon className={cfg.iconClass} strokeWidth={1.75} />
        <h2 className={`text-sm font-bold uppercase tracking-wide ${cfg.text}`}>{cfg.label}</h2>
        <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-white/60">
          {invoices.length}
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {invoices.length === 0 && (
          <div className="rounded-xl border border-dashed border-white/15 p-6 text-center text-xs text-white/40">
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
    <div className="mb-4 flex items-center gap-3 rounded-lg border border-brand-green/30 bg-white/[0.06] px-4 py-3">
      <Loader2 className="h-5 w-5 animate-spin text-brand-green" strokeWidth={1.75} />
      <span className="text-sm font-medium text-white">{PROCESSING_MESSAGES[i]}</span>
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
          <span className="h-9 w-1.5 rounded-full bg-brand-green" />
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-white/40">Platform › {TITLES[view]}</div>
            <h1 className="text-2xl font-semibold tracking-tight text-white">{TITLES[view]}</h1>
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
          className="flex items-center gap-2 rounded-lg bg-brand-green px-5 py-2.5 text-sm font-semibold text-brand-ink shadow-sm transition-colors duration-150 hover:bg-brand-greenHover disabled:cursor-not-allowed disabled:opacity-70"
        >
          {upload.isPending ? <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} /> : <Plus className="h-4 w-4" strokeWidth={1.75} />}
          {upload.isPending ? "Working…" : "Upload Invoice"}
        </button>
      </div>

      {upload.isPending && <ProcessingIndicator />}
      {upload.isError && (
        <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          Upload failed. Is the backend running on :8000?
        </div>
      )}
      {uploadResult && (
        <div className="mb-4 rounded-lg border border-white/10 bg-white/[0.05] p-4 text-sm text-white/70">
          Uploaded <span className="font-semibold text-brand-green">{uploadResult.uploaded}</span>
          {uploadResult.failed > 0 && (
            <>, <span className="text-rose-300">{uploadResult.failed} failed</span></>
          )}
          .
        </div>
      )}

      {isLoading && <div className="text-white/40">Loading invoices…</div>}
      {isError && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
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
