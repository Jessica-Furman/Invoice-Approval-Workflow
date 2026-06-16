import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboard } from "../api/client";
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

export function Dashboard({ view }: { view: View }) {
  const [selected, setSelected] = useState<number | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="text-xs text-slate-400">Platform › {TITLES[view]}</div>
          <h1 className="text-2xl font-bold text-slate-900">{TITLES[view]}</h1>
        </div>
        <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Upload Invoice
        </button>
      </div>

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
            <Column title="Flagged" dotClass="bg-rose-500" invoices={data.flagged} onSelect={setSelected} />
          )}
          {(view === "dashboard" || view === "matched") && (
            <Column title="Matched" dotClass="bg-blue-500" invoices={data.matched} onSelect={setSelected} />
          )}
          {(view === "dashboard" || view === "all") && (
            <Column title="All" dotClass="bg-slate-400" invoices={data.all} onSelect={setSelected} />
          )}
        </div>
      )}

      {selected !== null && (
        <DetailDrawer id={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
