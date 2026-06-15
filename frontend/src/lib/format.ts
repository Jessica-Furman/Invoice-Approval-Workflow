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
  matched: "bg-blue-100 text-blue-700",
  flagged: "bg-rose-100 text-rose-700",
  needs_manual_review: "bg-amber-100 text-amber-700",
  processing_failed: "bg-slate-200 text-slate-700",
};
