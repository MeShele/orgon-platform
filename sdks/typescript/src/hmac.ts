import { createHmac, randomUUID } from "node:crypto";

export interface SignedHeaders {
  "X-ORGON-Key": string;
  "X-ORGON-Timestamp": string;
  "X-ORGON-Nonce": string;
  "X-ORGON-Signature": string;
}

/**
 * Compute the signature exactly as MerchantHMACAuthMiddleware expects:
 *
 *   msg = `${ts}\n${nonce}\n${METHOD}\n${path}\n` + raw body bytes
 *   sig = hex(HMAC-SHA256(secret, msg))
 *
 * `path` is the URL path only (no host, no query string is signed —
 * matches server). `body` is the exact bytes the client sends; for
 * GET/DELETE pass "" .
 */
export function buildSignedHeaders(opts: {
  apiKey: string;
  secret: string;
  method: string;
  path: string;
  body: string;
}): SignedHeaders {
  const ts = Date.now().toString();
  const nonce = randomUUID();
  const message = `${ts}\n${nonce}\n${opts.method.toUpperCase()}\n${opts.path}\n${opts.body}`;
  const sig = createHmac("sha256", opts.secret).update(message).digest("hex");
  return {
    "X-ORGON-Key": opts.apiKey,
    "X-ORGON-Timestamp": ts,
    "X-ORGON-Nonce": nonce,
    "X-ORGON-Signature": sig,
  };
}
