import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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
  line_item_count: number;
  matched_line_count: number;
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

/** Generate the Coupa import CSV for a matched invoice and trigger a browser download.
 *  POST (not a plain link) because generating stamps coupa_csv_generated_at + logs an audit event. */
export async function generateCoupaCsv(id: number): Promise<void> {
  const res = await api.post(`/api/invoices/${id}/coupa.csv`, null, {
    responseType: "blob",
  });
  const disposition = String(res.headers["content-disposition"] ?? "");
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? `coupa_${id}.csv`;

  const url = URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
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

export interface ClaritySummary {
  timesheets: number;
  projects: number;
  contractors: number;
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
