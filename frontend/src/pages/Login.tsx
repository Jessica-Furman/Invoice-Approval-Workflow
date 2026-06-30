import { useState } from "react";
import { Loader2, Lock, Mail } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

/** Email + password sign-in. Real credential checking happens in the backend later; for now the
 *  mock AuthContext just validates the email domain so the flow is clickable. */
export function Login({ onSwitchToSignup }: { onSwitchToSignup: () => void }) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signIn(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-brand-inkdark">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-500">Sign in to process your invoices.</p>
      </div>

      <Field label="Work email" icon={Mail}>
        <input
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@upbound.com"
          className={inputClass}
          required
        />
      </Field>

      <Field label="Password" icon={Lock}>
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          className={inputClass}
          required
        />
      </Field>

      {error && <p className="text-sm font-medium text-red-600">{error}</p>}

      <button type="submit" disabled={busy} className={submitClass}>
        {busy && <Loader2 className="h-4 w-4 animate-spin" />}
        Sign in
      </button>

      {/* OAuth seam — Microsoft Entra, wired in the auth milestone. */}
      <button
        type="button"
        disabled
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white py-2.5 text-sm font-medium text-slate-400"
        title="Coming soon"
      >
        <MicrosoftLogo className="h-4 w-4" />
        Continue with Microsoft (coming soon)
      </button>

      <p className="text-center text-sm text-slate-500">
        Don&apos;t have an account?{" "}
        <button type="button" onClick={onSwitchToSignup} className={linkClass}>
          Create one
        </button>
      </p>
    </form>
  );
}

// Shared form primitives (kept local to the auth pages).
export const inputClass =
  "w-full rounded-lg border border-slate-200 bg-white pl-10 pr-3 py-2.5 text-sm transition focus:border-brand-lime focus:shadow-glow focus:outline-none";
export const submitClass =
  "flex w-full items-center justify-center gap-2 rounded-lg bg-brand-inkdark py-2.5 text-sm font-semibold text-white transition hover:bg-brand-ink disabled:opacity-60";
export const linkClass = "font-semibold text-brand-limedark hover:underline";

/** Microsoft four-square brand mark (lucide has no brand logos). */
export function MicrosoftLogo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 21 21" className={className} aria-hidden="true">
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  );
}

export function Field({
  label,
  icon: Icon,
  children,
}: {
  label: string;
  icon: typeof Mail;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        {children}
      </div>
    </label>
  );
}
