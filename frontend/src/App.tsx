import {
  FileText,
  Flag,
  LayoutGrid,
  CheckCircle2,
  Settings,
} from "lucide-react";
import { Dashboard } from "./pages/Dashboard";

const navItems = [
  { label: "Dashboard", icon: LayoutGrid, active: true },
  { label: "Flagged Invoices", icon: Flag, active: false },
  { label: "Matched Invoices", icon: CheckCircle2, active: false },
  { label: "All Invoices", icon: FileText, active: false },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r border-slate-200 bg-white">
        <div className="px-6 py-5 text-lg font-bold text-slate-900">InVoicee</div>
        <nav className="flex-1 space-y-1 px-3">
          {navItems.map((item) => (
            <a
              key={item.label}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${
                item.active
                  ? "bg-blue-50 font-medium text-blue-700"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </a>
          ))}
        </nav>
        <div className="border-t border-slate-100 p-3">
          <a className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50">
            <Settings className="h-4 w-4" />
            Settings
          </a>
          <div className="mt-2 flex items-center gap-3 px-3 py-2">
            <div className="h-8 w-8 rounded-full bg-slate-200" />
            <div className="text-xs">
              <div className="font-medium text-slate-700">Invoice Processor</div>
              <div className="text-slate-400">Accounts Payable</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1">
        <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-8 py-3">
          <input
            placeholder="Search invoices, vendors, or IDs…"
            className="w-full max-w-xl rounded-lg border border-slate-200 px-4 py-2 text-sm focus:border-blue-400 focus:outline-none"
          />
        </header>
        <main className="p-8">
          <Dashboard />
        </main>
      </div>
    </div>
  );
}
