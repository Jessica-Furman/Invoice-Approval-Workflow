import { useState } from "react";
import { CheckCircle2, FileText, ShieldCheck } from "lucide-react";
import { Login } from "./Login";
import { Signup } from "./Signup";

/** Full-screen, unauthenticated shell: branded left panel + the login/signup card on the right.
 *  Toggling between the two is local state (the app has no router); the real OAuth redirect flow
 *  slots in here later. */
export function AuthScreen() {
  const [mode, setMode] = useState<"login" | "signup">("login");

  return (
    <div className="flex min-h-screen">
      {/* Brand panel — Upbound ink with lime accents, mirrors the app sidebar. */}
      <aside className="relative hidden w-1/2 flex-col justify-between bg-brand-inkdark p-12 lg:flex">
        <div>
          <img src="/logo.png" alt="inVoicee" className="h-11 w-auto" />
        </div>

        <div className="space-y-6">
          <h2 className="text-3xl font-bold leading-tight text-white">
            Contractor invoices,
            <br />
            matched and routed.
          </h2>
          <ul className="space-y-3 text-slate-300">
            <Bullet icon={FileText}>Parse invoice PDFs automatically</Bullet>
            <Bullet icon={CheckCircle2}>Match hours against Clarity timekeeping</Bullet>
            <Bullet icon={ShieldCheck}>Your invoices stay private to your account</Bullet>
          </ul>
        </div>

        <p className="text-xs text-slate-500">Upbound Group · Accounts Payable</p>
      </aside>

      {/* Form side */}
      <main className="flex w-full items-center justify-center bg-slate-50 p-6 lg:w-1/2">
        <div className="w-full max-w-sm">
          {/* Compact logo for narrow screens where the brand panel is hidden. */}
          <div className="mb-8 lg:hidden">
            <img src="/logo.png" alt="inVoicee" className="h-9 w-auto" />
          </div>

          {mode === "login" ? (
            <Login onSwitchToSignup={() => setMode("signup")} />
          ) : (
            <Signup onSwitchToLogin={() => setMode("login")} />
          )}
        </div>
      </main>
    </div>
  );
}

function Bullet({ icon: Icon, children }: { icon: typeof FileText; children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-3 text-sm">
      <Icon className="h-5 w-5 shrink-0 text-brand-lime" />
      {children}
    </li>
  );
}
