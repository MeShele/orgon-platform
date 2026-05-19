#!/usr/bin/env bash
# scripts/phase_1_smoke.sh
#
# Post-deploy smoke for Wave 29 (Phase 1 dfns-grade hardening).
# Each section reports a single line: ✅ pass / ❌ fail / ⚠️ skip.
# Non-zero exit if any required check fails — designed to gate
# a "promote preview → prod" decision.
#
# Usage:
#   BASE_URL=https://orgon-preview.asystem.ai ./scripts/phase_1_smoke.sh
#
#   # With merchant key — runs idempotency replay test:
#   BASE_URL=https://orgon-preview.asystem.ai \
#     ORGON_KEY=okt_… ORGON_SECRET=okst_… \
#     ./scripts/phase_1_smoke.sh
#
# Requires: bash 4+, curl, jq, openssl, uuidgen.

set -u
set -o pipefail

BASE_URL="${BASE_URL:?BASE_URL env var required, e.g. https://orgon-preview.asystem.ai}"
ORGON_KEY="${ORGON_KEY:-}"
ORGON_SECRET="${ORGON_SECRET:-}"

PASS=0
FAIL=0
SKIP=0
FAILS=()

_pass() { printf '  \033[32m✅\033[0m %s\n' "$1"; PASS=$((PASS+1)); }
_fail() { printf '  \033[31m❌\033[0m %s — %s\n' "$1" "${2:-}"; FAIL=$((FAIL+1)); FAILS+=("$1"); }
_skip() { printf '  \033[33m⚠️\033[0m  %s — %s\n' "$1" "${2:-}"; SKIP=$((SKIP+1)); }

_header() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# ────────────────────────────────────────────────────────────────────
_header "1. Reachability & basic health"

curl -fsS -m 10 "${BASE_URL}/api/health" > /tmp/orgon-health.json 2>&1 \
  && _pass "/api/health 200" \
  || _fail "/api/health 200" "got $(cat /tmp/orgon-health.json 2>/dev/null | head -c 200)"

if jq -e '.status == "ok"' /tmp/orgon-health.json > /dev/null 2>&1; then
  _pass "/api/health body shape (status=ok)"
else
  _fail "/api/health body" "expected .status='ok', got $(cat /tmp/orgon-health.json 2>/dev/null | head -c 200)"
fi

curl -fsS -m 10 "${BASE_URL}/v1/health/extended" > /tmp/orgon-v1-extended.json 2>&1 \
  && _pass "/v1/health/extended 200" \
  || _fail "/v1/health/extended 200" "got $(cat /tmp/orgon-v1-extended.json 2>/dev/null | head -c 200)"

if jq -e '.webhook_queue.pending != null and .deposit_watcher.lag_seconds != null' \
     /tmp/orgon-v1-extended.json > /dev/null 2>&1; then
  _pass "/v1/health/extended exposes webhook_queue + deposit_watcher"
else
  _fail "/v1/health/extended body shape" \
        "expected .webhook_queue.pending and .deposit_watcher.lag_seconds — got $(cat /tmp/orgon-v1-extended.json)"
fi

# ────────────────────────────────────────────────────────────────────
_header "2. RequestId/RBAC envelope on /v1/* errors (E-02)"

# Unauthenticated /v1/ping should be 401 with the canonical envelope
# {error, message, request_id}. Failing this means the error reshape
# middleware or the request-id middleware regressed.
# NOTE: no `-f` here — curl --fail short-circuits on 4xx/5xx and
# skips writing the body file, which is exactly the shape we want
# to inspect. Use -sS + manual status check instead.
OUT="$(curl -sS -m 10 -o /tmp/orgon-401.json -w 'HTTP_STATUS=%{http_code}\nX_REQUEST_ID=%header{x-request-id}\n' \
  "${BASE_URL}/v1/ping" 2>&1 || true)"

if echo "$OUT" | grep -q 'HTTP_STATUS=401'; then
  _pass "GET /v1/ping returns 401 without HMAC"
else
  _fail "GET /v1/ping unauthenticated status" "expected 401, got: $OUT"
fi

if echo "$OUT" | grep -qE 'X_REQUEST_ID=[a-f0-9]{8,}'; then
  _pass "X-Request-Id header present on 401"
else
  _fail "X-Request-Id on 401 response" "header missing — RequestIdAndErrorMiddleware regressed?"
fi

if jq -e '.error != null and .message != null and .request_id != null' \
     /tmp/orgon-401.json > /dev/null 2>&1; then
  _pass "401 body has canonical envelope {error,message,request_id}"
else
  _fail "401 envelope shape" "got: $(cat /tmp/orgon-401.json 2>/dev/null | head -c 200)"
fi

# ────────────────────────────────────────────────────────────────────
_header "3. Audit query API (E-04) — auth-gated"

# Without JWT, /api/audit/events MUST refuse access (401 or 403),
# never 200. A 500 would suggest the route itself is broken.
# No `-f` — see /v1/ping note above; we want the body on 4xx.
OUT="$(curl -sS -m 10 -o /tmp/orgon-audit-anon.json -w '%{http_code}' \
  "${BASE_URL}/api/audit/events" 2>&1 || true)"

case "$OUT" in
  401|403)
    _pass "/api/audit/events refuses unauthenticated access (HTTP $OUT)"
    ;;
  500)
    _fail "/api/audit/events" "500 Internal Server Error — route or service crashed"
    ;;
  *)
    _fail "/api/audit/events without JWT" "expected 401/403, got $OUT — body: $(cat /tmp/orgon-audit-anon.json 2>/dev/null | head -c 200)"
    ;;
esac

# Same for /api/audit/events.csv — must NOT stream CSV to anonymous.
OUT="$(curl -sS -m 10 -o /tmp/orgon-audit-csv.bin -w '%{http_code}' \
  "${BASE_URL}/api/audit/events.csv" 2>&1 || true)"

case "$OUT" in
  401|403)
    _pass "/api/audit/events.csv refuses unauthenticated access (HTTP $OUT)"
    ;;
  *)
    _fail "/api/audit/events.csv without JWT" "expected 401/403, got $OUT"
    ;;
esac

# ────────────────────────────────────────────────────────────────────
_header "4. Idempotency-Key replay (E-01) — needs merchant key"

if [[ -z "$ORGON_KEY" || -z "$ORGON_SECRET" ]]; then
  _skip "idempotency replay" "ORGON_KEY/ORGON_SECRET not set — pass them to run this check"
else
  _do_signed_get() {
    local path="$1"
    local idem="$2"
    local ts nonce sig msg
    ts=$(date +%s%3N)
    nonce=$(uuidgen)
    # Server signing message: f"{ts}\n{nonce}\n{METHOD}\n{path}\n".encode() + raw_body
    # GET body is empty.
    msg=$(printf '%s\n%s\nGET\n%s\n' "$ts" "$nonce" "$path")
    sig=$(printf '%s' "$msg" | openssl dgst -sha256 -hmac "$ORGON_SECRET" -hex | awk '{print $2}')

    curl -fsS -m 10 -o /tmp/orgon-idem.json -w 'HTTP=%{http_code} REPLAY=%header{x-orgon-idempotent-replay}\n' \
      -H "X-ORGON-Key: $ORGON_KEY" \
      -H "X-ORGON-Timestamp: $ts" \
      -H "X-ORGON-Nonce: $nonce" \
      -H "X-ORGON-Signature: $sig" \
      -H "X-ORGON-Idempotency-Key: $idem" \
      "${BASE_URL}${path}" 2>&1 || true
  }

  # /v1/ping is the safest authenticated endpoint to probe — pure
  # echo, no merchant-side state change.
  IDEM=$(uuidgen)
  OUT1="$(_do_signed_get /v1/ping "$IDEM")"
  sleep 1
  OUT2="$(_do_signed_get /v1/ping "$IDEM")"

  # Note: idempotency caches ONLY mutating methods (POST/PATCH/PUT/DELETE).
  # GET passes through. So we expect REPLAY= (empty) on both calls —
  # any other behaviour indicates the cache scope is wrong.
  if echo "$OUT1$OUT2" | grep -qE 'REPLAY=1'; then
    _fail "idempotency scope on GET" \
          "X-ORGON-Idempotent-Replay was set on a GET — cache must skip non-mutating verbs"
  else
    _pass "idempotency cache correctly skips GET (mutating-only scope)"
  fi
fi

# ────────────────────────────────────────────────────────────────────
_header "5. Webhook delivery v2 headers (E-03)"

# We can't easily verify outbound webhook headers from this script
# without an integrator endpoint. Closest we can do: confirm the
# delivery worker is running by sampling /v1/health/extended.
WEBHOOK_PENDING=$(jq -r '.webhook_queue.pending // empty' /tmp/orgon-v1-extended.json)
WEBHOOK_AGE=$(jq -r '.webhook_queue.oldest_pending_age_seconds // empty' /tmp/orgon-v1-extended.json)

if [[ -n "$WEBHOOK_PENDING" ]]; then
  _pass "webhook queue depth reported: $WEBHOOK_PENDING pending"
else
  _fail "webhook queue depth missing in /v1/health/extended"
fi

if [[ -n "$WEBHOOK_AGE" ]] && [[ "$WEBHOOK_AGE" -gt 3600 ]]; then
  _fail "oldest pending webhook age" "${WEBHOOK_AGE}s > 1h — delivery worker may be stuck"
elif [[ -n "$WEBHOOK_AGE" ]]; then
  _pass "oldest pending webhook age: ${WEBHOOK_AGE}s (under 1h ceiling)"
fi

# ────────────────────────────────────────────────────────────────────
_header "6. Deposit watcher lag (sanity, not part of Wave 29 but quick)"

WATCH_LAG=$(jq -r '.deposit_watcher.lag_seconds // empty' /tmp/orgon-v1-extended.json)
WATCH_ERR=$(jq -r '.deposit_watcher.errored_wallets // 0' /tmp/orgon-v1-extended.json)

if [[ -n "$WATCH_LAG" ]] && [[ "$WATCH_LAG" -gt 600 ]]; then
  _fail "deposit_watcher lag" "${WATCH_LAG}s > 10 min — watcher may be down"
elif [[ -n "$WATCH_LAG" ]]; then
  _pass "deposit_watcher lag: ${WATCH_LAG}s"
fi

if [[ "$WATCH_ERR" -gt 0 ]]; then
  _fail "deposit_watcher errored_wallets" "$WATCH_ERR wallets in error streak"
else
  _pass "deposit_watcher errored_wallets: 0"
fi

# ────────────────────────────────────────────────────────────────────
_header "Summary"

printf 'pass=%d fail=%d skip=%d\n' "$PASS" "$FAIL" "$SKIP"
if [[ "$FAIL" -gt 0 ]]; then
  printf '\nFailed checks:\n'
  for f in "${FAILS[@]}"; do printf '  - %s\n' "$f"; done
  exit 1
fi
printf '\nSchema migrations 047-051 cannot be verified from this script\n'
printf '(needs DB access). On Coolify SSH:\n'
printf '  psql "$DATABASE_URL" -c \"SELECT version FROM schema_migrations WHERE version LIKE %s\" \\\n' "'04%' OR version LIKE '05%'"
printf '\nExpected 5 rows: 047_idempotency_keys, 048_request_id_columns,\n'
printf '049_webhook_retention, 050_audit_query_indexes, 051_policy_engine_extend.\n'
exit 0
