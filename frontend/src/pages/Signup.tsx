import { useState } from "react";
import { BadgeCheck, Loader2, Lock, Mail, User } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { ACCESS_HINT } from "../auth/access";
import { Field, inputClass, linkClass, submitClass } from "./Login";

/** Create-account form. Collects the fields the access rule needs — a corporate email + employee ID
 *  (validated client-side here, and authoritatively in the backend later). */
export function Signup({ onSwitchToLogin }: { onSwitchToLogin: () => void }) {
  const { signUp } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signUp({ name, email, employeeId, password });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-up failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-brand-inkdark">Create your account</h1>
        <p className="mt-1 text-sm text-slate-500">{ACCESS_HINT}</p>
      </div>

      <Field label="Full name" icon={User}>
        <input
          type="text"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Jane Doe"
          className={inputClass}
          required
        />
      </Field>

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

      <Field label="Employee ID" icon={BadgeCheck}>
        <input
          type="text"
          inputMode="numeric"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          placeholder="123456"
          className={inputClass}
          required
        />
      </Field>

      <Field label="Password" icon={Lock}>
        <input
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
          className={inputClass}
          required
        />
      </Field>

      {error && <p className="text-sm font-medium text-red-600">{error}</p>}

      <button type="submit" disabled={busy} className={submitClass}>
        {busy && <Loader2 className="h-4 w-4 animate-spin" />}
        Create account
      </button>

      <p className="text-center text-sm text-slate-500">
        Already have an account?{" "}
        <button type="button" onClick={onSwitchToLogin} className={linkClass}>
          Sign in
        </button>
      </p>
    </form>
  );
}
