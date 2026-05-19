/**
 * ASystem Core ↔ ORGON end-to-end smoke harness.
 *
 * Standalone Deno script (no npm install). Mirrors asystem-core's
 * `supabase/functions/_shared/orgon-client.ts` byte-for-byte so a
 * green run here proves the HMAC layer + endpoint contracts match
 * what edge functions actually send. Web Crypto API for parity
 * with the Deno runtime; no Node-only imports.
 *
 * Usage:
 *   ORGON_KEY=okt_… \
 *   ORGON_SECRET=okst_… \
 *   ORGON_BASE_URL=https://orgon.asystem.ai \
 *     deno run --allow-net --allow-env smoke.ts
 *
 * Exit code 0 on full pass, 1 on the first failed step (we want to
 * bail eagerly so the failure context isn't drowned by cascade).
 */

const KEY = Deno.env.get("ORGON_KEY") ?? "";
const SECRET = Deno.env.get("ORGON_SECRET") ?? "";
const BASE = (Deno.env.get("ORGON_BASE_URL") ?? "https://orgon.asystem.ai").replace(/\/$/, "");

if (!KEY || !SECRET) {
  console.error("ORGON_KEY and ORGON_SECRET env vars are required.");
  Deno.exit(2);
}

// ────────────────────────────────────────────────────────────────
// HMAC — same canonical message ORGON's middleware expects:
//   `${ts_ms}\n${nonce}\n${METHOD}\n${path}\n${rawBody}`
// ────────────────────────────────────────────────────────────────

async function hmacSha256Hex(secret: string, message: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

interface CallResult<T = unknown> {
  ok: boolean;
  status: number;
  data: T | null;
  error: string | null;
  requestId: string | null;
}

async function call<T = unknown>(
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  body?: Record<string, unknown>,
): Promise<CallResult<T>> {
  const bodyStr = body ? JSON.stringify(body) : "";
  const ts = String(Date.now());
  const nonce = crypto.randomUUID();
  const canonical = `${ts}\n${nonce}\n${method.toUpperCase()}\n${path}\n${bodyStr}`;
  const sig = await hmacSha256Hex(SECRET, canonical);
  const headers: Record<string, string> = {
    "X-ORGON-Key": KEY,
    "X-ORGON-Timestamp": ts,
    "X-ORGON-Nonce": nonce,
    "X-ORGON-Signature": sig,
    Accept: "application/json",
  };
  if (bodyStr) headers["Content-Type"] = "application/json";

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: bodyStr || undefined,
  });
  const text = await res.text();
  let data: T | null = null;
  let error: string | null = null;
  try {
    if (text) data = JSON.parse(text) as T;
  } catch {
    error = text.slice(0, 500);
  }
  if (!res.ok && !error) error = text.slice(0, 500);
  return {
    ok: res.ok,
    status: res.status,
    data: res.ok ? data : null,
    error,
    requestId: res.headers.get("x-request-id"),
  };
}

// ────────────────────────────────────────────────────────────────
// Output helpers
// ────────────────────────────────────────────────────────────────

let stepCount = 0;
function pass(label: string, detail?: string) {
  stepCount += 1;
  console.log(`  ✓ ${stepCount}. ${label}${detail ? ` — ${detail}` : ""}`);
}
function fail(label: string, detail: string): never {
  stepCount += 1;
  console.error(`  ✗ ${stepCount}. ${label} — ${detail}`);
  Deno.exit(1);
}
function section(name: string) {
  console.log(`\n${name}`);
}

// ────────────────────────────────────────────────────────────────
// Smoke
// ────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log(`ORGON smoke against ${BASE}`);
  console.log(`Key: ${KEY.slice(0, 8)}…\n`);

  // ── Phase 1 — HMAC + ping ──────────────────────────────────────
  section("Phase 1 — HMAC + ping");

  const ping = await call<{ merchant_id?: string; scopes?: string[] }>("GET", "/v1/ping");
  if (!ping.ok) fail("GET /v1/ping", `status=${ping.status} err=${ping.error}`);
  if (!ping.data?.merchant_id) {
    fail("GET /v1/ping payload", "missing merchant_id in response");
  }
  const merchantId = ping.data!.merchant_id!;
  pass("GET /v1/ping authenticates", `merchant=${merchantId}`);

  // ── Phase 2 — user + wallet provisioning ───────────────────────
  section("Phase 2 — user + wallet provisioning");

  const externalId = `smoke-${crypto.randomUUID()}`;
  const email = `${externalId}@asystem.local`;

  const u1 = await call<{ id: string; external_id: string }>("POST", "/v1/users", {
    external_id: externalId,
    email,
  });
  if (!u1.ok) fail("POST /v1/users (insert)", `status=${u1.status} err=${u1.error}`);
  if (u1.data!.external_id !== externalId) {
    fail("POST /v1/users payload", `returned external_id=${u1.data!.external_id}`);
  }
  const userId = u1.data!.id;
  pass("POST /v1/users creates user", `id=${userId}`);

  const u2 = await call<{ id: string }>("POST", "/v1/users", {
    external_id: externalId,
    email,
  });
  if (!u2.ok) fail("POST /v1/users (re-call)", `status=${u2.status} err=${u2.error}`);
  if (u2.data!.id !== userId) {
    fail("POST /v1/users idempotency", `re-call returned different id ${u2.data!.id} (expected ${userId})`);
  }
  pass("POST /v1/users idempotent on external_id", `same id on re-call`);

  // Sandbox testnet only. tron-nile = 5010 is the asystem-core default.
  const w1 = await call<{ id: string; status: string; address: string | null }>("POST", "/v1/wallets", {
    network: "5010",
    end_user_id: userId,
  });
  if (!w1.ok) fail("POST /v1/wallets", `status=${w1.status} err=${w1.error}`);
  if (!w1.data!.id || !w1.data!.status) {
    fail("POST /v1/wallets payload", "missing id or status");
  }
  const walletId = w1.data!.id;
  pass(
    "POST /v1/wallets provisions",
    `id=${walletId} status=${w1.data!.status} addr=${w1.data!.address ?? "<pending>"}`,
  );

  const w2 = await call<{ id: string }>("GET", `/v1/wallets/${walletId}`);
  if (!w2.ok) fail("GET /v1/wallets/{id}", `status=${w2.status} err=${w2.error}`);
  if (w2.data!.id !== walletId) {
    fail("GET /v1/wallets/{id} payload", `id mismatch ${w2.data!.id}`);
  }
  pass("GET /v1/wallets/{id} returns the same row");

  // ── Phase 3 — webhook config + synthetic delivery ──────────────
  section("Phase 3 — webhook config + synthetic delivery");

  const dummyUrl = "https://example.invalid/orgon-smoke-target";
  const dummySecret = crypto.randomUUID().replace(/-/g, "");

  const cfg = await call<{ url: string; secret_set: boolean }>("PUT", "/v1/webhooks/config", {
    url: dummyUrl,
    secret: dummySecret,
  });
  if (!cfg.ok) fail("PUT /v1/webhooks/config", `status=${cfg.status} err=${cfg.error}`);
  if (cfg.data!.url !== dummyUrl) {
    fail("PUT /v1/webhooks/config payload", `url didn't round-trip (got ${cfg.data!.url})`);
  }
  if (!cfg.data!.secret_set) {
    fail("PUT /v1/webhooks/config payload", "secret_set=false after write");
  }
  pass("PUT /v1/webhooks/config persists url+secret");

  const cfgGet = await call<{ url: string; secret_set: boolean }>("GET", "/v1/webhooks/config");
  if (!cfgGet.ok) fail("GET /v1/webhooks/config", `status=${cfgGet.status} err=${cfgGet.error}`);
  if (cfgGet.data!.url !== dummyUrl) {
    fail("GET /v1/webhooks/config payload", `url mismatch ${cfgGet.data!.url}`);
  }
  pass("GET /v1/webhooks/config reads back what we wrote");

  const t = await call<{ delivery_id: string; queued: boolean }>("POST", "/v1/webhooks/test", {
    event_type: "asystem.smoke.test",
    payload: { note: "smoke harness — ignore" },
  });
  if (!t.ok) fail("POST /v1/webhooks/test", `status=${t.status} err=${t.error}`);
  if (!t.data!.delivery_id) {
    fail("POST /v1/webhooks/test payload", "no delivery_id returned");
  }
  pass("POST /v1/webhooks/test queued", `delivery=${t.data!.delivery_id}`);

  const deliveries = await call<{ deliveries: Array<{ id: string; event_type: string }> }>(
    "GET",
    "/v1/webhooks/deliveries?limit=5",
  );
  if (!deliveries.ok) {
    fail("GET /v1/webhooks/deliveries", `status=${deliveries.status} err=${deliveries.error}`);
  }
  const found = deliveries.data!.deliveries.some((d) => d.id === t.data!.delivery_id);
  if (!found) {
    fail("GET /v1/webhooks/deliveries", `test delivery ${t.data!.delivery_id} not in last 5`);
  }
  pass("GET /v1/webhooks/deliveries surfaces the test delivery");

  // ── Done ────────────────────────────────────────────────────────
  console.log(`\nAll ${stepCount} checks passed against ${BASE}.`);
  console.log("HMAC, idempotency, provisioning, and webhook surfaces match the asystem-core contract.");
}

await main();
