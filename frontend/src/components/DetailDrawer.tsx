import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  FileWarning,
  Trash2,
  UserX,
  X,
} from "lucide-react";
import {
  deleteInvoice,
  fetchClarityEntries,
  fetchInvoice,
  generateCoupaCsv,
  generateCoupaDraftCsv,
  invoiceExcelUrl,
  invoicePdfUrl,
  type ClarityProject,
  type InvoiceDetail as InvoiceDetailT,
  type LineItem,
} from "../api/client";
import { date, money, parseMethodBadge, statusChip, statusLabel } from "../lib/format";

function sum(nums: (number | null | undefined)[]): number {
  return nums.reduce((acc: number, n) => acc + (n ?? 0), 0);
}

function num(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}
function str(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}

type MismatchReasonT = InvoiceDetailT["mismatch_reasons"][number];

/** Icon + label for a mismatch field ("hours" -> Clock "Hours mismatch", etc.). */
function fieldMeta(field: string): { Icon: typeof Clock; label: string } {
  const f = field.toLowerCase();
  if (f.includes("hour")) return { Icon: Clock, label: "Hours mismatch" };
  if (f.includes("name")) return { Icon: UserX, label: "Contractor not found" };
  if (f.includes("document") || f.includes("parse")) return { Icon: FileWarning, label: "Document issue" };
  return { Icon: AlertTriangle, label: field };
}

/** Pull the contractor name out of a reason sentence so it can be shown as a clear "Who". */
function whoFromReason(r: MismatchReasonT): string | null {
  if (r.field.toLowerCase().includes("name") && r.invoice_value) return r.invoice_value;
  const m =
    r.reason.match(/(?:for|hours for)\s+([A-Z][^(.,:]+?)(?:\s*\(|\.|,|:|$)/) ||
    r.reason.match(/^([A-Z][^(.,:]+?):/);
  return m ? m[1].trim() : null;
}

/** One compact issue row: icon · Who + field · invoice→clarity values · muted reason. */
function MismatchRow({ r }: { r: MismatchReasonT }) {
  const { Icon, label } = fieldMeta(r.field);
  const who = whoFromReason(r);
  const hasValues = r.invoice_value != null || r.clarity_value != null;
  return (
    <div className="flex items-start gap-2.5 px-3 py-2.5">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate text-sm font-semibold text-slate-800">{who ?? label}</span>
          <span className="shrink-0 text-[11px] uppercase tracking-wide text-slate-400">{label}</span>
          {hasValues && (
            <span className="ml-auto shrink-0 font-mono text-xs text-slate-500">
              <span className="text-slate-700">{r.invoice_value ?? "—"}</span>
              <span className="mx-1 text-slate-300">→</span>
              <span className="text-slate-700">{r.clarity_value ?? "—"}</span>
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs leading-snug text-slate-500">{r.reason}</p>
      </div>
    </div>
  );
}

/** Date-level breakdown shown when a Clarity contractor row is expanded. */
function ClarityBreakdown({ invoiceId, lineId }: { invoiceId: number; lineId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["clarity-entries", invoiceId, lineId],
    queryFn: () => fetchClarityEntries(invoiceId, lineId),
  });

  if (isLoading) return <div className="px-4 py-3 text-xs text-slate-400">Loading entries…</div>;
  if (!data || data.length === 0)
    return <div className="px-4 py-3 text-xs text-slate-400">No Clarity entries in this period.</div>;

  const included = data.filter((e) => e.included);
  return (
    <div className="bg-slate-50 px-4 py-3">
      <div className="mb-2 text-xs font-medium text-slate-500">
        How this total was summed — {included.length} counted of {data.length} entries in period
        (time-off & non-posted excluded)
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-slate-400">
            <th className="py-1 font-medium">Date Worked</th>
            <th className="py-1 font-medium">Project</th>
            <th className="py-1 font-medium">Task</th>
            <th className="py-1 font-medium">Status</th>
            <th className="py-1 text-right font-medium">Hours</th>
          </tr>
        </thead>
        <tbody>
          {data.map((e) => (
            <tr
              key={e.id}
              className={`border-t border-slate-200 ${e.included ? "" : "text-slate-400 line-through"}`}
            >
              <td className="py-1">{date(e.date_worked)}</td>
              <td className="py-1">{e.investment_name ?? e.project_id ?? "—"}</td>
              <td className="py-1">{e.task_name ?? "—"}</td>
              <td className="py-1">
                {e.is_time_off
                  ? "Time off"
                  : e.time_sheet_status ?? (e.is_posted ? "Posted" : "Not posted")}
                {!e.included && (
                  <span className="ml-1 rounded bg-slate-200 px-1 text-[10px] text-slate-600 no-underline">
                    excluded
                  </span>
                )}
              </td>
              <td className="py-1 text-right font-mono">{e.hours ?? "—"}</td>
            </tr>
          ))}
          <tr className="border-t border-slate-300 font-semibold">
            <td className="py-1" colSpan={4}>
              Counted total
            </td>
            <td className="py-1 text-right font-mono">{sum(included.map((e) => e.hours))}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/** A single aligned comparison row: invoice line on the left, matched Clarity on the right.
 *  `clarityDuplicate` = this Clarity contractor's total was already shown on an earlier row
 *  (single-contractor invoices aggregate every line to the same person), so its Clarity cells are
 *  blanked here to avoid double-showing — and double-counting — the same hours. */
function ComparisonRow({
  invoiceId,
  li,
  clarityDuplicate,
}: {
  invoiceId: number;
  li: LineItem;
  clarityDuplicate: boolean;
}) {
  const [open, setOpen] = useState(false);
  const diff = li.diff ?? {};
  const clarityName = str(diff["clarity_name"]);
  const clarityHours = num(diff["clarity_hours"]);
  const delta = num(diff["hours_delta"]);
  const resolved = str(diff["match_method"]) && str(diff["match_method"]) !== "unresolved";
  const bad = li.line_status && li.line_status !== "matched";

  return (
    <>
      <tr className={`border-b border-slate-100 ${bad ? "bg-amber-50" : ""}`}>
        {/* Invoice side */}
        <td className="py-2 pl-1 text-slate-700">{li.contractor_name}</td>
        <td className="py-2 text-right text-slate-600">{li.hours ?? "—"}</td>
        <td className="py-2 text-right text-slate-500">{li.rate ?? "—"}</td>
        <td className="py-2 text-right font-mono text-slate-800">{money(li.amount)}</td>
        {/* divider */}
        <td className="w-px bg-slate-200 p-0" />
        {/* Clarity side */}
        <td className="py-2 pl-3">
          {clarityDuplicate ? (
            <span className="text-xs italic text-slate-400">↳ counted above</span>
          ) : resolved ? (
            <button
              onClick={() => setOpen((o) => !o)}
              className="flex items-center gap-1 text-left text-slate-700 hover:text-blue-700"
            >
              {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              {clarityName ?? li.contractor_name}
            </button>
          ) : (
            <span className="text-amber-600">no match</span>
          )}
        </td>
        <td className="py-2 text-right text-slate-600">
          {clarityDuplicate ? "" : clarityHours ?? "—"}
        </td>
        <td
          className={`py-2 pr-1 text-right font-mono ${
            !clarityDuplicate && delta && Math.abs(delta) > 0.001 ? "text-amber-700" : "text-slate-400"
          }`}
        >
          {clarityDuplicate ? "" : delta === null ? "—" : delta > 0 ? `+${delta}` : delta}
        </td>
      </tr>
      {open && !clarityDuplicate && (
        <tr>
          <td colSpan={7} className="p-0">
            <ClarityBreakdown invoiceId={invoiceId} lineId={li.id} />
          </td>
        </tr>
      )}
    </>
  );
}

/** Sum of Clarity hours counting each Clarity contractor once — so a single-contractor invoice whose
 *  lines all aggregate to the same person shows that person's total once, not once per invoice line. */
function distinctClarityHours(items: LineItem[]): number {
  const seen = new Set<string>();
  let total = 0;
  for (const li of items) {
    const diff = li.diff ?? {};
    const key = str(diff["clarity_name"]);
    const hours = num(diff["clarity_hours"]) ?? 0;
    if (key === null) {
      total += hours; // unresolved line — keep its own value (typically 0)
    } else if (!seen.has(key)) {
      seen.add(key);
      total += hours;
    }
  }
  return total;
}

function ComparisonTable({ data }: { data: InvoiceDetailT }) {
  // Mark rows whose Clarity contractor already appeared above (aggregated single-contractor invoices),
  // so the Clarity column shows each contractor's total exactly once.
  const seenClarity = new Set<string>();
  const rows = data.line_items.map((li) => {
    const key = str((li.diff ?? {})["clarity_name"]);
    const duplicate = key !== null && seenClarity.has(key);
    if (key !== null) seenClarity.add(key);
    return { li, duplicate };
  });

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
          <th className="pb-1" colSpan={4}>
            Invoice Data
          </th>
          <th className="pb-1" />
          <th className="pb-1" colSpan={3}>
            Clarity Data
          </th>
        </tr>
        <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
          <th className="py-2 pl-1 font-medium">Contractor</th>
          <th className="py-2 text-right font-medium">Hours</th>
          <th className="py-2 text-right font-medium">Rate</th>
          <th className="py-2 text-right font-medium">Amount</th>
          <th className="p-0" />
          <th className="py-2 pl-3 font-medium">Contractor</th>
          <th className="py-2 text-right font-medium">Hours</th>
          <th className="py-2 pr-1 text-right font-medium">Δ</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ li, duplicate }) => (
          <ComparisonRow key={li.id} invoiceId={data.id} li={li} clarityDuplicate={duplicate} />
        ))}
        <tr className="font-semibold">
          <td className="py-2 pl-1">Total</td>
          <td className="py-2 text-right">{sum(data.line_items.map((l) => l.hours))}</td>
          <td />
          <td className="py-2 text-right font-mono">{money(sum(data.line_items.map((l) => l.amount)))}</td>
          <td className="p-0" />
          <td className="py-2 pl-3" />
          <td className="py-2 text-right">{distinctClarityHours(data.line_items)}</td>
          <td />
        </tr>
      </tbody>
    </table>
  );
}

/** "Cloud Operations - Support and Maintenance (PR00123)" — name with its Clarity project ID
 * alongside, falling back to whichever of the two is present. */
function projectLabel(p: ClarityProject): string {
  if (p.project_name && p.project_id) return `${p.project_name} (${p.project_id})`;
  return p.project_name ?? p.project_id ?? "—";
}

function ProjectTable({ rows }: { rows: ClarityProject[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
          <th className="py-2 font-medium">Type</th>
          <th className="py-2 font-medium">Project</th>
          <th className="py-2 font-medium">Company Code</th>
          <th className="py-2 font-medium">Cost Center</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr key={p.id} className="border-b border-slate-100">
            <td className="py-2 text-slate-700">{p.capex_opex ?? "—"}</td>
            <td className="py-2 text-slate-600">{projectLabel(p)}</td>
            <td className="py-2 text-slate-600">{p.cost_code ?? "—"}</td>
            <td className="py-2 text-slate-600">{p.cost_center ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function DetailDrawer({ id, onClose }: { id: number; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => fetchInvoice(id),
  });

  const del = useMutation({
    mutationFn: () => deleteInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });

  const csv = useMutation({
    mutationFn: () => generateCoupaCsv(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
    },
  });

  const draftCsv = useMutation({
    mutationFn: () => generateCoupaDraftCsv(id),
  });

  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-slate-900/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {isLoading || !data ? (
          <div className="p-10 text-slate-400">Loading…</div>
        ) : (
          <div className="p-6">
            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
              <button
                onClick={onClose}
                className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800"
              >
                <ArrowLeft className="h-4 w-4" />
                {data.invoice_number} — {date(data.date_received)}
              </button>
              <div className="flex items-center gap-3">
                {(() => {
                  const badge = parseMethodBadge(data.parse_method);
                  return badge ? (
                    <span
                      className={`rounded px-2 py-1 text-xs font-semibold ${badge.cls}`}
                      title="How this invoice was parsed"
                    >
                      {badge.label}
                    </span>
                  ) : null;
                })()}
                <span className={`rounded px-2 py-1 text-xs font-semibold ${statusChip[data.status]}`}>
                  {statusLabel[data.status]}
                </span>
                <button onClick={onClose} className="rounded p-1 hover:bg-slate-100">
                  <X className="h-5 w-5 text-slate-500" />
                </button>
              </div>
            </div>

            {/* Meta */}
            <div className="mb-4 flex flex-wrap gap-x-8 gap-y-1 text-sm text-slate-600">
              <span>Vendor: <span className="font-medium text-slate-800">{data.vendor_name}</span></span>
              <span>
                Period: {date(data.payment_period_start)} – {date(data.payment_period_end)}
              </span>
              <span>
                Match: {data.matched_line_count}/{data.line_item_count}
              </span>
              {data.parse_confidence != null && (
                <span>
                  Parse confidence:{" "}
                  <span className="font-medium text-slate-800">
                    {(data.parse_confidence * 100).toFixed(0)}%
                  </span>
                </span>
              )}
              {data.routed_to && (
                <span>
                  Routed to: <span className="font-medium capitalize text-slate-800">{data.routed_to}</span> inbox
                </span>
              )}
              {data.pdf_storage_key && (
                <a
                  href={invoicePdfUrl(data.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-blue-600 hover:underline"
                >
                  <FileText className="h-4 w-4" />
                  {data.pdf_storage_key}
                </a>
              )}
            </div>

            {/* Mismatch reasons — compact, professional list */}
            {data.mismatch_reasons.length > 0 && (
              <div className="mb-6 overflow-hidden rounded-lg border border-slate-200 bg-white">
                <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-3 py-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                    What didn’t match
                  </span>
                  <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">
                    {data.mismatch_reasons.length}
                  </span>
                </div>
                <div className="divide-y divide-slate-100">
                  {data.mismatch_reasons.map((m, i) => (
                    <MismatchRow key={i} r={m} />
                  ))}
                </div>
              </div>
            )}

            {/* Aligned comparison */}
            <div className="mb-2 text-xs text-slate-400">
              Tip: click a contractor under Clarity Data to see the date-level breakdown.
            </div>
            <ComparisonTable data={data} />

            {/* Projects */}
            <div className="mt-10">
              <h3 className="mb-2 text-lg font-semibold text-slate-800">Clarity Project Details</h3>
              {data.clarity_projects.length > 0 ? (
                <ProjectTable rows={data.clarity_projects} />
              ) : (
                <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">
                  No linked Clarity projects.
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="mt-8 flex items-center justify-between gap-3">
              {confirmingDelete ? (
                <div className="flex items-center gap-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2">
                  <span className="text-sm text-rose-700">
                    Delete this invoice? This can’t be undone.
                  </span>
                  <button
                    onClick={() => del.mutate()}
                    disabled={del.isPending}
                    className="rounded-lg bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-60"
                  >
                    {del.isPending ? "Deleting…" : "Yes, delete"}
                  </button>
                  <button
                    onClick={() => setConfirmingDelete(false)}
                    disabled={del.isPending}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-white"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmingDelete(true)}
                  className="flex items-center gap-1.5 rounded-lg border border-rose-300 px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete Invoice
                </button>
              )}

              <div className="flex gap-3">
                <a
                  href={invoiceExcelUrl(data.id)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
                >
                  Export to Excel
                </a>
                {data.status === "matched" ? (
                  <button
                    onClick={() => csv.mutate()}
                    disabled={csv.isPending}
                    className="rounded-lg bg-brand-green px-4 py-2 text-sm font-semibold text-brand-ink shadow-sm transition-colors duration-150 hover:bg-brand-greenHover disabled:opacity-60"
                  >
                    {csv.isPending ? "Generating…" : "Approve & Create CSV"}
                  </button>
                ) : (
                  <button
                    onClick={() => draftCsv.mutate()}
                    disabled={draftCsv.isPending}
                    className="rounded-lg bg-brand-ink px-4 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-brand-navy disabled:opacity-60"
                  >
                    {draftCsv.isPending ? "Generating…" : "Create Draft CSV File"}
                  </button>
                )}
              </div>
            </div>
            {data.coupa_csv_generated_at && !csv.isError && (
              <div className="mt-3 text-right text-xs text-slate-400">
                Coupa CSV last generated {date(data.coupa_csv_generated_at)}.
              </div>
            )}
            {csv.isError && (
              <div className="mt-3 text-right text-sm text-rose-600">
                Couldn’t generate the Coupa CSV. Only matched invoices are eligible — is the backend running?
              </div>
            )}
            {draftCsv.isError && (
              <div className="mt-3 text-right text-sm text-rose-600">
                Couldn’t generate the draft CSV. This invoice may have no matched contractors yet.
              </div>
            )}
            {del.isError && (
              <div className="mt-3 text-right text-sm text-rose-600">
                Couldn’t delete the invoice. Is the backend running?
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
