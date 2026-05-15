import { Deposit } from "../types";

type Req = <T>(method: string, path: string, body?: unknown, query?: Record<string, string | number | undefined>) => Promise<T>;

export class DepositsAPI {
  constructor(private readonly req: Req) {}

  listForWallet(
    walletId: string,
    opts?: { cursor?: string; limit?: number },
  ): Promise<{ deposits: Deposit[]; next_cursor: string | null }> {
    return this.req("GET", `/v1/wallets/${walletId}/deposits`, undefined, opts);
  }

  listForUser(
    userId: string,
    opts?: { cursor?: string; limit?: number },
  ): Promise<{ deposits: Deposit[]; next_cursor: string | null }> {
    return this.req("GET", `/v1/users/${userId}/deposits`, undefined, opts);
  }
}
