import { User } from "../types";

type Req = <T>(method: string, path: string, body?: unknown, query?: Record<string, string | number | undefined>) => Promise<T>;

export class UsersAPI {
  constructor(private readonly req: Req) {}

  /** Idempotent on (merchant, external_id). Repeat calls update email/kyc/metadata. */
  create(body: {
    external_id: string;
    email: string;
    kyc_status?: string;
    metadata?: Record<string, unknown>;
  }): Promise<User> {
    return this.req<User>("POST", "/v1/users", body);
  }

  get(id: string): Promise<User> {
    return this.req<User>("GET", `/v1/users/${id}`);
  }

  list(opts?: { cursor?: string; limit?: number }): Promise<{ users: User[]; next_cursor: string | null }> {
    return this.req("GET", "/v1/users", undefined, opts);
  }

  update(
    id: string,
    body: { email?: string; kyc_status?: string; metadata?: Record<string, unknown> },
  ): Promise<User> {
    return this.req<User>("PATCH", `/v1/users/${id}`, body);
  }
}
