/**
 * Auth state for the app — currently a MOCK so we can build and see the login/signup UI before the
 * backend, OAuth, and the `users` table exist.
 *
 * Seams for the real implementation (M-auth):
 *  - `signIn`/`signUp` currently fake-validate and persist a user to localStorage. Swap their bodies
 *    to call the backend (`POST /api/auth/login` / `/api/auth/signup`) and store the returned token.
 *  - On a logged-in user we set the `X-User-Id` header on the shared axios client. That's the exact
 *    seam the backend will read for per-user invoice scoping (see plan: get_current_user dependency).
 *    Today nothing reads it — it's harmless and pre-wires the integration.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api/client";
import { isAllowedEmail, isValidEmployeeId } from "./access";

export interface AuthUser {
  /** Stand-in id until the backend issues real ones. Becomes the X-User-Id value. */
  id: string;
  name: string;
  email: string;
  employeeId: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (input: SignUpInput) => Promise<void>;
  signOut: () => void;
}

export interface SignUpInput {
  name: string;
  email: string;
  employeeId: string;
  password: string;
}

const STORAGE_KEY = "invoicee.auth.user";
const AuthContext = createContext<AuthContextValue | null>(null);

/** Push (or clear) the per-user header on the shared axios client. */
function applyUserHeader(user: AuthUser | null) {
  if (user) api.defaults.headers.common["X-User-Id"] = user.id;
  else delete api.defaults.headers.common["X-User-Id"];
}

function loadStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = loadStoredUser();
    applyUserHeader(stored);
    return stored;
  });

  // Keep localStorage + axios header in sync whenever the user changes.
  useEffect(() => {
    applyUserHeader(user);
    if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    else localStorage.removeItem(STORAGE_KEY);
  }, [user]);

  const signIn = useCallback(async (email: string, password: string) => {
    // MOCK: accept any allowed-domain email + non-empty password. Replace with a real API call.
    await new Promise((r) => setTimeout(r, 400));
    if (!isAllowedEmail(email)) {
      throw new Error("Use your Upbound Group or RAC email to sign in.");
    }
    if (!password) throw new Error("Enter your password.");
    setUser({
      id: email.toLowerCase(),
      name: nameFromEmail(email),
      email: email.toLowerCase(),
      employeeId: "",
    });
  }, []);

  const signUp = useCallback(async (input: SignUpInput) => {
    // MOCK: enforce the access rule client-side, then "create" the account locally.
    await new Promise((r) => setTimeout(r, 400));
    if (!input.name.trim()) throw new Error("Enter your full name.");
    if (!isAllowedEmail(input.email)) {
      throw new Error("Sign-up is limited to Upbound Group or RAC email addresses.");
    }
    if (!isValidEmployeeId(input.employeeId)) {
      throw new Error("Enter a valid 6-digit employee ID.");
    }
    if (input.password.length < 8) {
      throw new Error("Password must be at least 8 characters.");
    }
    setUser({
      id: input.email.toLowerCase(),
      name: input.name.trim(),
      email: input.email.toLowerCase(),
      employeeId: input.employeeId.trim(),
    });
  }, []);

  const signOut = useCallback(() => setUser(null), []);

  const value = useMemo(
    () => ({ user, signIn, signUp, signOut }),
    [user, signIn, signUp, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

/** "jane.doe@upbound.com" -> "Jane Doe" (display fallback when we don't collect a name at login). */
function nameFromEmail(email: string): string {
  const local = email.split("@")[0] ?? "";
  return (
    local
      .split(/[._-]+/)
      .filter(Boolean)
      .map((p) => p[0]?.toUpperCase() + p.slice(1))
      .join(" ") || email
  );
}
