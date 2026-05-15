import { createHmac, timingSafeEqual } from "node:crypto";
import { WebhookConfig, WebhookDelivery } from "../types";

type Req = <T>(method: string, path: string, body?: unknown, query?: Record<string, string | number | undefined>) => Promise<T>;

export class WebhooksAPI {
  constructor(private readonly req: Req) {}

  config = {
    get: (): Promise<WebhookConfig> =>
      this.req<WebhookConfig>("GET", "/v1/webhooks/config"),
    update: (body: { url?: string; secret?: string }): Promise<WebhookConfig> =>
      this.req<WebhookConfig>("PUT", "/v1/webhooks/config", body),
  };

  deliveries(opts?: {
    cursor?: string;
    limit?: number;
  }): Promise<{ deliveries: WebhookDelivery[]; next_cursor: string | null }> {
    return this.req("GET", "/v1/webhooks/deliveries", undefined, opts);
  }

  /**
   * Verify an incoming webhook payload's signature.
   *
   * Usage in an Express/Fastify handler:
   *
   *   if (!OrgonClient.verifyWebhook({
   *     secret: process.env.WEBHOOK_SECRET!,
   *     timestamp: req.header("X-ORGON-Webhook-Timestamp")!,
   *     signature: req.header("X-ORGON-Webhook-Signature")!,
   *     rawBody: req.rawBody,
   *   })) { return res.status(401).end(); }
   */
  static verify(opts: {
    secret: string;
    timestamp: string | number;
    signature: string;
    rawBody: Buffer | string;
    /** Tolerance in ms. Default 5 min, same as our server-side window. */
    toleranceMs?: number;
  }): boolean {
    const tol = opts.toleranceMs ?? 5 * 60 * 1000;
    const tsMs = Number(opts.timestamp);
    if (!Number.isFinite(tsMs)) return false;
    if (Math.abs(Date.now() - tsMs) > tol) return false;

    const bodyBuf = typeof opts.rawBody === "string" ? Buffer.from(opts.rawBody, "utf8") : opts.rawBody;
    const expected = createHmac("sha256", opts.secret)
      .update(`${tsMs}\n`)
      .update(bodyBuf)
      .digest("hex");
    const a = Buffer.from(expected);
    const b = Buffer.from(opts.signature ?? "");
    if (a.length !== b.length) return false;
    return timingSafeEqual(a, b);
  }
}
