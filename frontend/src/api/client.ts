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

export async function fetchDashboard(): Promise<DashboardResponse> {
  const { data } = await api.get<DashboardResponse>("/api/dashboard");
  return data;
}

export async function fetchInvoice(id: number): Promise<InvoiceDetail> {
  const { data } = await api.get<InvoiceDetail>(`/api/invoices/${id}`);
  return data;
}
