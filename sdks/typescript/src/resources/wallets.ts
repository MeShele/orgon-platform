import { Wallet } from "../types";

type Req = <T>(method: string, path: string, body?: unknown, query?: Record<string, string | number | undefined>) => Promise<T>;

export class WalletsAPI {
  constructor(private readonly req: Req) {}

  /** Provision a user-deposit wallet or a treasury wallet on `network`. */
  create(body: {
    network: string | number;
    /** Either set end_user_id (user deposit) OR treasury (merchant-owned). */
    end_user_id?: string;
    treasury?: "treasury" | "fee" | "hot" | "cold";
    info?: string;
  }): Promise<Wallet> {
    return this.req<Wallet>("POST", "/v1/wallets", {
      ...body,
      network: String(body.network),
    });
  }

  get(id: string): Promise<Wallet> {
    return this.req<Wallet>("GET", `/v1/wallets/${id}`);
  }

  listForUser(userId: string): Promise<{ wallets: Wallet[] }> {
    return this.req("GET", `/v1/users/${userId}/wallets`);
  }
}
