import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Upload } from "lucide-react";
import { fetchClaritySummary, importClarity, type ClarityImportResult } from "../api/client";

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
    <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white px-4 py-3">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <Database className="h-4 w-4 text-slate-400" />
        <span className="font-medium text-slate-700">Clarity data</span>
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
          className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          <Upload className="h-4 w-4" />
          {mutation.isPending ? "Importing…" : "Import Clarity export"}
        </button>
      </div>
    </div>
  );
}
