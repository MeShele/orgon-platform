import { buildSignedHeaders } from "./hmac";
import {
  OrgonClientOptions,
  OrgonError,
} from "./types";
import { UsersAPI } from "./resources/users";
import { WalletsAPI } from "./resources/wallets";
import { TransactionsAPI } from "./resources/transactions";
import { DepositsAPI } from "./resources/deposits";
import { WebhooksAPI } from "./resources/webhooks";

const DEFAULT_BASE = "https://orgon.asystem.ai";

export class OrgonClient {
  readonly users: UsersAPI;
  readonly wallets: WalletsAPI;
  readonly transactions: TransactionsAPI;
  readonly deposits: DepositsAPI;
  readonly webhooks: WebhooksAPI;

  private readonly apiKey: string;
  private readonly secret: string;
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(opts: OrgonClientOptions) {
    if (!opts.apiKey) throw new Error("OrgonClient: apiKey required");
    if (!opts.secret) throw new Error("OrgonClient: secret required");
    this.apiKey = opts.apiKey;
    this.secret = opts.secret;
    this.baseUrl = (opts.baseUrl ?? DEFAULT_BASE).replace(/\/+$/, "");
    this.fetchImpl = opts.fetchImpl ?? fetch;

    // Resource sub-clients all share the same private request() —
    // hides HMAC signing from each one and keeps retry/error logic
    // in a single place.
    this.users = new UsersAPI(this.request.bind(this));
    this.wallets = new WalletsAPI(this.request.bind(this));
    this.transactions = new TransactionsAPI(this.request.bind(this));
    this.deposits = new DepositsAPI(this.request.bind(this));
    this.webhooks = new WebhooksAPI(this.request.bind(this));
  }

  /** True if this client is bound to a sandbox key (okt_*). */
  get sandbox(): boolean {
    return this.apiKey.startsWith("okt_");
  }

  /**
   * Authenticated ping. Useful as a `clientHealthCheck` to verify a
   * fresh integration before wiring real flows.
   */
  async ping(): Promise<{ ok: boolean; merchant_id: string; scopes: string[]; api_key_id: string }> {
    return this.request("GET", "/v1/ping");
  }

  /** Public, unsigned. Anyone can hit this to verify reachability. */
  async health(): Promise<{ status: string; service: string }> {
    const r = await this.fetchImpl(`${this.baseUrl}/v1/health`);
    return r.json() as Promise<{ status: string; service: string }>;
  }

  async request<T = unknown>(
    method: string,
    path: string,
    body?: unknown,
    query?: Record<string, string | number | undefined>,
  ): Promise<T> {
    const url = this.buildUrl(path, query);
    const raw = body !== undefined ? JSON.stringify(body) : "";
    const headers = {
      "Content-Type": "application/json",
      ...buildSignedHeaders({
        apiKey: this.apiKey,
        secret: this.secret,
        method,
        path: new URL(url).pathname,
        body: raw,
      }),
    };

    const res = await this.fetchImpl(url, {
      method,
      headers,
      body: raw === "" ? undefined : raw,
    });

    const text = await res.text();
    let parsed: unknown = undefined;
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = text;
      }
    }

    if (!res.ok) {
      const msg =
        (parsed && typeof parsed === "object" && "error" in parsed
          ? String((parsed as { error: unknown }).error)
          : null) ?? `ORGON ${res.status}`;
      throw new OrgonError(res.status, parsed, msg);
    }
    return parsed as T;
  }

  private buildUrl(path: string, query?: Record<string, string | number | undefined>): string {
    let u = `${this.baseUrl}${path}`;
    if (query) {
      const params = new URLSearchParams();
      for (const [k, v] of Object.entries(query)) {
        if (v === undefined || v === null || v === "") continue;
        params.set(k, String(v));
      }
      const q = params.toString();
      if (q) u += `?${q}`;
    }
    return u;
  }
}
