import axios from "axios";

// Default to 127.0.0.1 (not "localhost"): uvicorn binds IPv4 127.0.0.1, but on Windows
// "localhost" often resolves to IPv6 ::1 first, so the browser hits a refused [::1]:8000.
const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const api = axios.create({ baseURL });

// ---- Types (mirror backend schemas) ----
export type Status =
  | "matched"
  | "flagged"
  | "needs_manual_review"
  | "processing_failed";

export interface InvoiceSummary {
  id: number;
  vendor_name: string | null;
  invoice_number: string | null;
  date_received: string | null;
  payment_period_start: string | null;
  payment_period_end: string | null;
  total_invoice_cost: number | null;
  status: Status;
  routed_to: string | null;
  archived_at: string | null;
  line_item_count: number;
  matched_line_count: number;
  /** "rules" | "ocr" | "template" (auto-learned) | "llm" | "rules+llm" */
  parse_method: string | null;
}

export interface MismatchReason {
  field: string;
  reason: string;
  invoice_value: string | null;
  clarity_value: string | null;
}

export interface LineItem {
  id: number;
  contractor_name: string | null;
  hours: number | null;
  rate: number | null;
  amount: number | null;
  line_status: string | null;
  diff: Record<string, unknown> | null;
  matched_clarity_id: number | null;
}

export interface ClarityTimesheet {
  id: number;
  contractor_name: string | null;
  hours: number | null;
  rate: number | null;
  period_start: string | null;
  period_end: string | null;
  project_id: string | null;
}

export interface ClarityProject {
  id: number;
  project_id: string | null;
  project_name: string | null;
  budget_id: string | null;
  cost_code: string | null;
  capex_opex: string | null;
  cost_center: string | null;
  vendor: string | null;
  lob: string | null;
  spend: number | null;
}

export interface InvoiceDetail extends InvoiceSummary {
  mismatch_reasons: MismatchReason[];
  pdf_storage_key: string | null;
  parse_confidence: number | null;
  coupa_csv_generated_at: string | null;
  line_items: LineItem[];
  clarity_timesheets: ClarityTimesheet[];
  clarity_projects: ClarityProject[];
}

export interface DashboardResponse {
  flagged: InvoiceSummary[];
  matched: InvoiceSummary[];
  all: InvoiceSummary[];
}

export function invoicePdfUrl(id: number): string {
  return `${baseURL}/api/invoices/${id}/pdf`;
}

export function invoiceExcelUrl(id: number): string {
  return `${baseURL}/api/invoices/${id}/export.xlsx`;
}

/** POST an endpoint that returns a file blob and trigger a browser download, honoring the
 *  server's Content-Disposition filename (exposed via CORS) with a fallback. */
async function downloadFromPost(
  url: string,
  fallbackName: string,
  body: unknown = null,
): Promise<void> {
  const res = await api.post(url, body, { responseType: "blob" });
  const disposition = String(res.headers["content-disposition"] ?? "");
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? fallbackName;

  const objectUrl = URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}

/** Generate the Coupa import CSV for a MATCHED invoice and download it.
 *  POST (not a plain link) because generating stamps coupa_csv_generated_at + logs an audit event. */
export function generateCoupaCsv(id: number): Promise<void> {
  return downloadFromPost(`/api/invoices/${id}/coupa.csv`, `coupa_${id}.csv`);
}

/** Generate a DRAFT Coupa CSV for a FLAGGED invoice — lines for the matched contractors only. */
export function generateCoupaDraftCsv(id: number): Promise<void> {
  return downloadFromPost(`/api/invoices/${id}/coupa-draft.csv`, `DRAFT_coupa_${id}.csv`);
}

/** Bulk-export every matched invoice: downloads a ZIP of one CSV each, then archives them server-side
 *  (they clear from the board but stay in the DB / History). Powers the "Export All" slider. */
export function bulkExportMatched(): Promise<void> {
  return downloadFromPost(`/api/invoices/bulk-export-matched`, `coupa_export.zip`);
}

// --- Executive report ("Create Report") -------------------------------------------------------
// The LLM narrative runs ONLY when these are called — never in the background.
export interface ReportRequest {
  start_date?: string | null; // YYYY-MM-DD
  end_date?: string | null;
}

export interface ReportVendor {
  vendor: string;
  spend: number;
  invoice_count: number;
  type: string;
}

export interface ReportMonth {
  month: string; // YYYY-MM
  contractor_spend: number;
  other_spend: number;
  invoice_count: number;
}

export interface ReportAggregates {
  period: { start: string | null; end: string | null; generated_from_invoices: number };
  totals: {
    combined_spend: number;
    contractor_spend: number;
    other_spend: number;
    invoice_count: number;
    contractor_invoice_count: number;
    other_invoice_count: number;
    status_counts: Record<string, number>;
    parse_method_counts: Record<string, number>;
    avg_parse_confidence: number | null;
  };
  capex_opex: { amounts: Record<string, number>; pct: Record<string, number> };
  by_company: Record<string, { spend: number; company_code: string | null; cost_center: string | null }>;
  by_cost_center: Record<string, number>;
  by_vendor: ReportVendor[];
  monthly_trend: ReportMonth[];
}

export interface ReportResponse {
  aggregates: ReportAggregates;
  narrative: string | null;
  llm_available: boolean;
  generated_at: string;
}

/** Aggregate every processed invoice and (if a key is configured) write the AI executive narrative. */
export async function generateReport(body: ReportRequest): Promise<ReportResponse> {
  const { data } = await api.post<ReportResponse>("/api/reports", body);
  return data;
}

/** Download the same report as a self-contained standalone HTML file (opens offline, emailable). */
export function downloadReportHtml(body: ReportRequest): Promise<void> {
  return downloadFromPost("/api/reports/html", "invoice-report.html", body);
}

/** Every invoice ever (active + archived), for the History tab. Deleted invoices are excluded. */
export async function fetchHistory(): Promise<InvoiceSummary[]> {
  const { data } = await api.get<InvoiceSummary[]>("/api/history");
  return data;
}

export async function fetchDashboard(): Promise<DashboardResponse> {
  const { data } = await api.get<DashboardResponse>("/api/dashboard");
  return data;
}

export async function fetchInvoice(id: number): Promise<InvoiceDetail> {
  const { data } = await api.get<InvoiceDetail>(`/api/invoices/${id}`);
  return data;
}

export async function deleteInvoice(id: number): Promise<{ deleted: number }> {
  const { data } = await api.delete<{ deleted: number }>(`/api/invoices/${id}`);
  return data;
}

export interface ClarityEntry {
  id: number;
  date_worked: string | null;
  hours: number | null;
  project_id: string | null;
  investment_name: string | null;
  task_name: string | null;
  time_sheet_status: string | null;
  is_time_off: boolean;
  is_posted: boolean;
  included: boolean;
}

export async function fetchClarityEntries(
  invoiceId: number,
  lineItemId: number
): Promise<ClarityEntry[]> {
  const { data } = await api.get<ClarityEntry[]>(
    `/api/invoices/${invoiceId}/lines/${lineItemId}/clarity-entries`
  );
  return data;
}

export type ClaritySource = "api" | "csv_fallback" | "csv_manual" | "unconfigured";

export interface ClaritySummary {
  timesheets: number;
  projects: number;
  contractors: number;
  source: ClaritySource;
  last_synced_at: string | null;
  last_error: string | null;
}

export async function fetchClaritySummary(): Promise<ClaritySummary> {
  const { data } = await api.get<ClaritySummary>("/api/clarity/summary");
  return data;
}

export interface ClarityImportResult {
  file: string;
  source_rows: number;
  aggregated_rows: number;
  timesheets_created: number;
  timesheets_updated: number;
  projects_created: number;
  warnings: string[];
}

export interface UploadResultItem {
  filename: string;
  ok: boolean;
  invoice_id: number | null;
  invoice_number: string | null;
  status: Status | null;
  error: string | null;
}

export interface UploadResult {
  uploaded: number;
  failed: number;
  results: UploadResultItem[];
}

export async function uploadInvoices(files: File[]): Promise<UploadResult> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const { data } = await api.post<UploadResult>("/api/invoices/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function importClarity(file: File): Promise<ClarityImportResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<ClarityImportResult>("/api/clarity/import", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// ---- "Other Invoice Types" (hardware / software / subscription) ----
export type OtherStatus = "all_data_found" | "missing_data";

export interface OtherInvoiceSummary {
  id: number;
  vendor_name: string | null;
  invoice_number: string | null;
  date_received: string | null;
  total_invoice_cost: number | null;
  status: OtherStatus;
  supplier_number: string | null;
  budget_id: string | null;
  cost_center: string | null;
  offset_gl_account: string | null;
  approver: string | null;
  archived_at: string | null;
  line_item_count: number;
  missing_count: number;
}

export interface OtherLineItem {
  id: number;
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  amount: number | null;
}

export interface OtherInvoiceDetail extends OtherInvoiceSummary {
  pdf_storage_key: string | null;
  parse_confidence: number | null;
  missing_fields: string[];
  line_items: OtherLineItem[];
}

export interface OtherDashboardResponse {
  missing: OtherInvoiceSummary[];
  found: OtherInvoiceSummary[];
  all: OtherInvoiceSummary[];
}

export async function fetchOtherDashboard(): Promise<OtherDashboardResponse> {
  const { data } = await api.get<OtherDashboardResponse>("/api/other/dashboard");
  return data;
}

export async function fetchOtherInvoice(id: number): Promise<OtherInvoiceDetail> {
  const { data } = await api.get<OtherInvoiceDetail>(`/api/other/invoices/${id}`);
  return data;
}

export async function fetchOtherHistory(): Promise<OtherInvoiceSummary[]> {
  const { data } = await api.get<OtherInvoiceSummary[]>("/api/other/history");
  return data;
}

/** Upload hardware/software/subscription PDFs — runs the OTHER parser only (never contractor rules). */
export async function uploadOtherInvoices(files: File[]): Promise<UploadResult> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const { data } = await api.post<UploadResult>("/api/other/invoices/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
