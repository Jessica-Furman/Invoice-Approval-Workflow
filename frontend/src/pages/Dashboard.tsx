import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import { fetchDashboard, uploadInvoices, type UploadResult } from "../api/client";
import { ClarityBar } from "../components/ClarityBar";
import { Column } from "../components/Column";
import { DetailDrawer } from "../components/DetailDrawer";

export type View = "dashboard" | "flagged" | "matched" | "all";

const TITLES: Record<View, string> = {
  dashboard: "Invoice Overview",
  flagged: "Flagged Invoices",
  matched: "Matched Invoices",
  all: "All Invoices",
};

const PROCESSING_MESSAGES = ["Upload in progress…", "Parsing data…", "Processing data…"];

/** Animated banner shown while invoices upload: spinner + cycling status text. */
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
      <span className="ml-1 flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-lime [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-lime [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-lime" />
      </span>
    </div>
  );
}

export function Dashboard({ view }: { view: View }) {
  const [selected, setSelected] = useState<number | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  const upload = useMutation({
    mutationFn: uploadInvoices,
    onSuccess: (result) => {
      setUploadResult(result);
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["clarity-summary"] });
    },
  });

  function onFilesChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length) {
      setUploadResult(null);
      upload.mutate(files);
    }
    e.target.value = ""; // allow re-selecting the same file
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="h-10 w-1.5 rounded-full bg-brand-lime" />
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-400">Platform › {TITLES[view]}</div>
            <h1 className="text-2xl font-extrabold tracking-tight text-brand-ink">{TITLES[view]}</h1>
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
          {upload.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
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
        <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <div className="mb-2 font-medium text-slate-900">
            Processed {uploadResult.uploaded + uploadResult.failed} file
            {uploadResult.uploaded + uploadResult.failed === 1 ? "" : "s"} —{" "}
            <span className="text-emerald-600">{uploadResult.uploaded} ok</span>
            {uploadResult.failed > 0 && (
              <>, <span className="text-rose-600">{uploadResult.failed} failed</span></>
            )}
          </div>
          <ul className="space-y-1">
            {uploadResult.results.map((r, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className={r.ok ? "text-emerald-500" : "text-rose-500"}>
                  {r.ok ? "✓" : "✕"}
                </span>
                <span className="text-slate-700">{r.filename}</span>
                {r.ok ? (
                  <span className="text-slate-400">
                    → {r.invoice_number ?? `#${r.invoice_id}`} ({r.status})
                  </span>
                ) : (
                  <span className="text-rose-500">{r.error}</span>
                )}
              </li>
            ))}
          </ul>
          <button
            onClick={() => setUploadResult(null)}
            className="mt-3 text-xs text-slate-400 hover:text-slate-600"
          >
            Dismiss
          </button>
        </div>
      )}

      <ClarityBar />

      {isLoading && <div className="text-slate-400">Loading invoices…</div>}
      {isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Couldn’t reach the API. Is the backend running on :8000?
        </div>
      )}

      {data && (
        <div className="flex flex-wrap gap-6">
          {(view === "dashboard" || view === "flagged") && (
            <Column variant="flagged" invoices={data.flagged} onSelect={setSelected} />
          )}
          {(view === "dashboard" || view === "matched") && (
            <Column variant="matched" invoices={data.matched} onSelect={setSelected} />
          )}
          {(view === "dashboard" || view === "all") && (
            <Column variant="all" invoices={data.all} onSelect={setSelected} />
          )}
        </div>
      )}

      {selected !== null && (
        <DetailDrawer id={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
