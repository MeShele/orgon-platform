import { Transaction } from "../types";

type Req = <T>(method: string, path: string, body?: unknown, query?: Record<string, string | number | undefined>) => Promise<T>;

export class TransactionsAPI {
  constructor(private readonly req: Req) {}

  /** Initiate an outbound transfer. Returns in `pending`; call sign() to broadcast. */
  send(body: {
    wallet_id: string;
    to_address: string;
    amount: string;
    asset?: string;
    info?: string;
  }): Promise<Transaction> {
    return this.req<Transaction>("POST", "/v1/transactions", body);
  }

  sign(txId: string): Promise<Transaction> {
    return this.req<Transaction>("POST", `/v1/transactions/${txId}/sign`);
  }

  get(txId: string): Promise<Transaction> {
    return this.req<Transaction>("GET", `/v1/transactions/${txId}`);
  }

  list(opts?: {
    wallet_id?: string;
    cursor?: string;
    limit?: number;
  }): Promise<{ transactions: Transaction[]; next_cursor: string | null }> {
    return this.req("GET", "/v1/transactions", undefined, opts);
  }
}
