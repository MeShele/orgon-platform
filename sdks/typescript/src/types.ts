// Public types — mirror the JSON shapes returned by /v1/*. The SDK is
// hand-written rather than openapi-generated so they're easy to read
// and keep tight; any drift gets caught by integration tests in the
// monorepo.

export type Network = 1000 | 3000 | 3040 | 5000 | 5010;

export interface User {
  id: string;
  external_id: string;
  email: string;
  kyc_status: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Wallet {
  id: string;
  name: string;
  network: number;
  address: string | null;
  status: "pending" | "active";
  purpose: "treasury" | "fee" | "hot" | "cold" | "user_deposit";
  end_user_id: string | null;
  created_at: string;
}

export interface Transaction {
  id: string;
  wallet_name: string;
  to_address: string;
  value: string;
  token: string;
  network: number;
  tx_hash: string | null;
  status:
    | "pending"
    | "signed"
    | "broadcasted"
    | "confirmed"
    | "canceled"
    | "failed";
  created_at: string | null;
  updated_at: string | null;
}

export interface Deposit {
  id: string;
  wallet_id: string;
  end_user_id: string | null;
  network: number;
  tx_hash: string;
  log_index: number;
  from_address: string | null;
  to_address: string;
  asset: string;
  amount: string;
  confirmations: number;
  block_number: number | null;
  block_timestamp: string | null;
  discovered_at: string;
  status: "pending" | "confirmed" | "orphaned";
}

export interface WebhookConfig {
  url: string | null;
  secret_set: boolean;
}

export interface WebhookDelivery {
  id: string;
  event_type: string;
  attempts: number;
  last_status: number | null;
  last_error: string | null;
  next_retry_at: string | null;
  delivered_at: string | null;
  created_at: string;
}

export interface Page<T> {
  /** Returned by list endpoints; key varies (`users`, `wallets`, …). */
  data: T[];
  next_cursor: string | null;
}

export interface OrgonClientOptions {
  /** Public key, e.g. okl_… (live) or okt_… (sandbox). */
  apiKey: string;
  /** Secret returned ONCE at issue time. Keep in a vault. */
  secret: string;
  /** Defaults to https://orgon.asystem.ai. Override for staging. */
  baseUrl?: string;
  /** Override the http call (e.g. for testing). */
  fetchImpl?: typeof fetch;
}

export class OrgonError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
    message: string,
  ) {
    super(message);
    this.name = "OrgonError";
  }
}
