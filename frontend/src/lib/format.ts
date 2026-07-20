import type { Status } from "../api/client";

export function money(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function date(s: string | null | undefined): string {
  if (!s) return "—";
  const d = new Date(s + "T00:00:00");
  if (isNaN(d.getTime())) return s;
  return d.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" });
}

export const statusLabel: Record<Status, string> = {
  matched: "VERIFIED",
  flagged: "CONFLICT",
  needs_manual_review: "MISSING INFO",
  processing_failed: "FAILED",
};

export const statusChip: Record<Status, string> = {
  matched: "bg-emerald-100 text-emerald-700",
  flagged: "bg-amber-100 text-amber-800",
  needs_manual_review: "bg-amber-100 text-amber-700",
  processing_failed: "bg-slate-200 text-slate-700",
};

/** Badge for how the invoice was parsed. Only AI-involved methods get a badge —
 *  plain rules/OCR parsing is the norm and stays unlabeled. */
export function parseMethodBadge(
  method: string | null | undefined,
): { label: string; cls: string } | null {
  if (!method) return null;
  if (method.includes("llm")) {
    return { label: "AI-PARSED", cls: "bg-brand-navy/10 text-brand-navy" };
  }
  if (method === "template") {
    return { label: "AUTO-LEARNED", cls: "bg-sky-100 text-sky-700" };
  }
  return null;
}
