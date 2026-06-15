import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboard } from "../api/client";
import { Column } from "../components/Column";
import { DetailDrawer } from "../components/DetailDrawer";

export function Dashboard() {
  const [selected, setSelected] = useState<number | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="text-xs text-slate-400">Platform › Dashboard</div>
          <h1 className="text-2xl font-bold text-slate-900">Invoice Overview</h1>
        </div>
        <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Upload Invoice
        </button>
      </div>

      {isLoading && <div className="text-slate-400">Loading invoices…</div>}
      {isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Couldn’t reach the API. Is the backend running on :8000?
        </div>
      )}

      {data && (
        <div className="flex flex-wrap gap-6">
          <Column
            title="Flagged"
            dotClass="bg-rose-500"
            invoices={data.flagged}
            onSelect={setSelected}
          />
          <Column
            title="Matched"
            dotClass="bg-blue-500"
            invoices={data.matched}
            onSelect={setSelected}
          />
          <Column
            title="All"
            dotClass="bg-slate-400"
            invoices={data.all}
            onSelect={setSelected}
          />
        </div>
      )}

      {selected !== null && (
        <DetailDrawer id={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
