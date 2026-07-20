import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Upload } from "lucide-react";
import {
  fetchClaritySummary,
  importClarity,
  type ClarityImportResult,
  type ClaritySummary,
} from "../api/client";

/** Small always-on status dot: green while synced live from Clarity's API, amber for any fallback
 * state (API not configured, or a failed sync running on cached/manually-imported CSV data). */
function statusDot(summary: ClaritySummary | undefined) {
  if (!summary) return { color: "bg-slate-300", tooltip: "Clarity sync status loading…" };
  const synced = summary.last_synced_at
    ? new Date(summary.last_synced_at).toLocaleString()
    : null;
  switch (summary.source) {
    case "api":
      return { color: "bg-emerald-500", tooltip: `Live Clarity API — last synced ${synced ?? "just now"}` };
    case "csv_manual":
      return { color: "bg-amber-500", tooltip: `Using manually imported CSV export (${synced ?? "unknown time"})` };
    case "csv_fallback":
      return {
        color: "bg-amber-500",
        tooltip: `Clarity API unavailable${summary.last_error ? `: ${summary.last_error}` : ""} — showing cached/CSV data`,
      };
    default:
      return { color: "bg-amber-500", tooltip: "Clarity API not configured — using CSV export data" };
  }
}

export function ClarityBar() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const { data: summary } = useQuery({
    queryKey: ["clarity-summary"],
    queryFn: fetchClaritySummary,
  });

  const mutation = useMutation({
    mutationFn: importClarity,
    onSuccess: (r: ClarityImportResult) => {
      setMsg(
        `Imported ${r.file}: ${r.timesheets_created} new, ${r.timesheets_updated} updated, ` +
          `${r.projects_created} new projects (${r.source_rows.toLocaleString()} rows).`
      );
      qc.invalidateQueries({ queryKey: ["clarity-summary"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => setMsg("Import failed — check the file format."),
  });

  return (
    <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-xs">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-greenSoft/70">
          <Database className="h-4 w-4 text-brand-ink" strokeWidth={1.75} />
        </span>
        <span className="font-medium text-slate-700">Clarity data</span>
        <span
          className={`h-2 w-2 rounded-full ${statusDot(summary).color}`}
          title={statusDot(summary).tooltip}
        />
        {summary ? (
          <span className="text-slate-500">
            {summary.timesheets.toLocaleString()} timesheets ·{" "}
            {summary.contractors.toLocaleString()} contractors · {summary.projects} projects
          </span>
        ) : (
          <span className="text-slate-400">loading…</span>
        )}
      </div>

      <div className="ml-auto flex items-center gap-3">
        {msg && <span className="text-xs text-slate-500">{msg}</span>}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) mutation.mutate(f);
            e.target.value = "";
          }}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={mutation.isPending}
          className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors duration-150 hover:bg-slate-50 disabled:opacity-50"
        >
          <Upload className="h-4 w-4" strokeWidth={1.75} />
          {mutation.isPending ? "Importing…" : "Import Clarity export"}
        </button>
      </div>
    </div>
  );
}
