type Req = <T>(method: string, path: string, body?: unknown, query?: Record<string, string | number | undefined>) => Promise<T>;

export interface Invoice {
  id: string;
  billing_period: string;
  plan: string;
  currency: string;
  amount_total: string;
  items: { label: string; amount: number; qty?: number; unit?: number; unit_per_1000?: number }[];
  api_calls_total: number;
  tx_count_total: number;
  status: "open" | "paid" | "void";
  issued_at: string | null;
  paid_at: string | null;
}

export class InvoicesAPI {
  constructor(private readonly req: Req) {}

  /** Past invoices for the authenticated merchant. */
  list(opts?: { limit?: number }): Promise<{ invoices: Invoice[] }> {
    return this.req("GET", "/v1/invoices", undefined, opts);
  }
}
