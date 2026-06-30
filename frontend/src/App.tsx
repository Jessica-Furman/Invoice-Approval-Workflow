import { useState } from "react";
import {
  FileText,
  Flag,
  LayoutGrid,
  CheckCircle2,
  History as HistoryIcon,
  Settings,
  LogOut,
} from "lucide-react";
import { Dashboard, type View } from "./pages/Dashboard";
import { History } from "./pages/History";
import { SearchBar } from "./components/SearchBar";
import { AuthScreen } from "./pages/AuthScreen";
import { useAuth } from "./auth/AuthContext";

/** Two-character avatar initials from a display name ("Jane Doe" -> "JD"). */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const navItems: { label: string; icon: typeof LayoutGrid; view: View }[] = [
  { label: "Dashboard", icon: LayoutGrid, view: "dashboard" },
  { label: "Flagged Invoices", icon: Flag, view: "flagged" },
  { label: "Matched Invoices", icon: CheckCircle2, view: "matched" },
  { label: "All Invoices", icon: FileText, view: "all" },
  { label: "History", icon: HistoryIcon, view: "history" },
];

export default function App() {
  const { user, signOut } = useAuth();
  const [view, setView] = useState<View>("dashboard");
  const [search, setSearch] = useState("");

  // Unauthenticated -> show the login/signup screen instead of the app.
  if (!user) return <AuthScreen />;

  return (
    <div className="flex min-h-screen">
      {/* Sidebar — Upbound near-black with lime accents */}
      <aside className="flex w-60 flex-col bg-brand-inkdark">
        <div className="px-6 py-6">
          <img src="/logo.png" alt="inVoicee" className="h-10 w-auto" />
        </div>
        <nav className="flex-1 space-y-1.5 px-3">
          {navItems.map((item) => {
            const active = view === item.view;
            return (
              <button
                key={item.label}
                onClick={() => setView(item.view)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition ${
                  active
                    ? "bg-brand-lime font-semibold text-brand-inkdark shadow-[0_0_16px_rgba(164,214,30,0.45)]"
                    : "text-slate-200 hover:bg-white/10 hover:text-brand-lime"
                }`}
              >
                <item.icon className="h-[18px] w-[18px]" />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-3">
          <a className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/10 hover:text-brand-lime">
            <Settings className="h-4 w-4" />
            Settings
          </a>
          <div className="mt-2 flex items-center gap-3 px-3 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-lime text-sm font-bold text-brand-inkdark">
              {initials(user.name)}
            </div>
            <div className="min-w-0 flex-1 text-xs">
              <div className="truncate font-medium text-white">{user.name}</div>
              <div className="truncate text-slate-400">{user.email}</div>
            </div>
            <button
              onClick={signOut}
              title="Sign out"
              aria-label="Sign out"
              className="rounded-md p-1.5 text-slate-400 transition hover:bg-white/10 hover:text-brand-lime"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 bg-slate-50">
        <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-8 py-3">
          <SearchBar value={search} onChange={setSearch} />
        </header>
        <main className="p-8">
          {view === "history" ? (
            <History search={search} />
          ) : (
            <Dashboard view={view} search={search} />
          )}
        </main>
      </div>
    </div>
  );
}
