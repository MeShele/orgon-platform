// Tiny smoke tests for the HMAC signing helper. We can't bring in a
// full test runner without adding dev deps to a published SDK; these
// are plain assertion functions invoked from `node --test`.

import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { buildSignedHeaders } from "../hmac";

test("buildSignedHeaders produces the exact server-side message shape", () => {
  const apiKey = "okl_test";
  const secret = "oksl_secret";
  const headers = buildSignedHeaders({
    apiKey,
    secret,
    method: "post",
    path: "/v1/users",
    body: '{"external_id":"u1"}',
  });

  // Header set is complete.
  assert.equal(headers["X-ORGON-Key"], apiKey);
  assert.match(headers["X-ORGON-Timestamp"], /^\d+$/);
  assert.match(headers["X-ORGON-Nonce"], /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  assert.match(headers["X-ORGON-Signature"], /^[0-9a-f]{64}$/);

  // Signature reproducible by an independent computation using the
  // same scheme the server runs (middleware_merchant_hmac.py).
  const ts = headers["X-ORGON-Timestamp"];
  const nonce = headers["X-ORGON-Nonce"];
  const expected = createHmac("sha256", secret)
    .update(`${ts}\n${nonce}\nPOST\n/v1/users\n` + '{"external_id":"u1"}')
    .digest("hex");
  assert.equal(headers["X-ORGON-Signature"], expected);
});

test("buildSignedHeaders normalizes method to uppercase", () => {
  const a = buildSignedHeaders({
    apiKey: "k",
    secret: "s",
    method: "get",
    path: "/v1/health",
    body: "",
  });
  const b = buildSignedHeaders({
    apiKey: "k",
    secret: "s",
    method: "GET",
    path: "/v1/health",
    body: "",
  });
  // Different ts/nonce → different sig; but if we recompute with
  // a's ts/nonce as if the second call had been GET-uppercase, the
  // signature must match the actual a signature.
  const reproduced = createHmac("sha256", "s")
    .update(`${a["X-ORGON-Timestamp"]}\n${a["X-ORGON-Nonce"]}\nGET\n/v1/health\n`)
    .digest("hex");
  assert.equal(a["X-ORGON-Signature"], reproduced);
  assert.notEqual(a["X-ORGON-Signature"], b["X-ORGON-Signature"]);
});

test("buildSignedHeaders message includes the raw body byte-for-byte", () => {
  // Whitespace inside the body MUST be preserved verbatim — server
  // signs over raw bytes. This protects integrators who pretty-print
  // JSON locally from a silent mismatch.
  const body = '{\n  "external_id": "u1"\n}';
  const h = buildSignedHeaders({
    apiKey: "k",
    secret: "s",
    method: "POST",
    path: "/v1/users",
    body,
  });
  const expected = createHmac("sha256", "s")
    .update(`${h["X-ORGON-Timestamp"]}\n${h["X-ORGON-Nonce"]}\nPOST\n/v1/users\n` + body)
    .digest("hex");
  assert.equal(h["X-ORGON-Signature"], expected);
});
