# Tech Debt — running ledger

Honest inventory of issues found-but-not-fixed during recent work.
Each entry has: severity, where it lives, what would fix it, and
why it wasn't fixed in the original PR.

Severity scale:
* **L1 — silent prod risk.** Could lose data or mis-route money.
* **L2 — degrades trust over time.** Confusing logs, wrong audit,
  or surfaces missing tenant isolation when the table grows.
* **L3 — annoying.** CI noise, dev friction, duplicate code.

If you fix one of these, delete the entry. If you find a new one
while working on something else — add it here in the same PR.

---

## L1 — silent prod risk

### TD-1. `audit_log` has no `organization_id` — **PHASE A FIXED 2026-05-21, PHASE B PENDING**

**Phase A (landed 2026-05-21).** Additive column + populate from
known org-aware paths. No trigger touch, no bulk UPDATE, safe under
the append-only constraint.

* `backend/migrations/057_audit_log_organization_id.sql` — `ADD COLUMN
  IF NOT EXISTS organization_id uuid` (metadata-only on any-size
  table) + partial index `WHERE organization_id IS NOT NULL`.
  Idempotent, picks up automatically via `entrypoint.sh` overlay
  loader.
* `AuditService.log_action` — new optional `organization_id` kwarg,
  permissive coercion (UUID / str / garbage → None) so a stale caller
  passing the wrong type lands the row untagged instead of crashing
  the mutation flow.
* `compliance_service._write_audit` / `_write_rule_audit` — both
  accept `organization_id` and write it; 7 callers updated (claim /
  resolve / note / release_hold / rule create-update-delete). Source
  of org is the row being audited (alert.organization_id, rule.organization_id).
* `routes_platform_admin.py` self-service merchant create — writes
  the new merchant's id as `organization_id`, so merchant-facing
  audit endpoints (future) will return the provisioning event under
  the correct tenant.
* Tests: `test_audit_log_organization_id.py` (7 cases — UUID, str
  parsing, garbage coercion, missing kwarg, both compliance helpers,
  None for global rules).

What stayed NULL on purpose:
* Middleware-driven JWT audit rows (`middleware_audit_jwt`) — every
  request would need a `users → user_organizations` lookup. Phase B
  will cache the org via `request.state`.
* Historic rows pre-2026-05-21 — backfill needs the trigger lifted.

**Phase B (pending — separate change window).**
1. Backfill: `JOIN users → user_organizations` (or
   `details->>'partner_id'`) to populate historic rows in batches.
2. Trigger management: `ALTER TABLE audit_log DISABLE TRIGGER
   orgon_immutable_audit_log` for the backfill TX, re-enable after.
   Use SET LOCAL session_replication_role = replica if running
   inside a transaction that must keep the trigger semantically
   active for concurrent INSERTs.
3. Read-side filter in `/api/audit/*`: when caller is not
   super_admin / platform_admin, add `WHERE organization_id = $org`
   to both `_build_where` paths in `routes_audit.py`.
4. RLS policy enable + FORCE on `audit_log` — only once `/v1/*`
   surfaces audit endpoints to merchants.

**Why not in this session:** trigger drop + bulk UPDATE on a multi-
million-row table is exactly the operation memory
`feedback_no_rapid_deploys` and the "retire 039's destructive bulk-
tombstone UPDATE" commit warn against. Wants its own change-window
and dry-run on a recent prod snapshot.

### TD-2. ~~`signature_history` not populated for `/v1/*` sign + batch-sign~~ — **FIXED 2026-05-21**

All three sign code-paths now write the same canonical row.

Resolution did NOT thread SignatureService through the other callers
(that would have forced a wholesale dependency-injection rewrite —
tenant-scoped clients vs the singleton platform client, telegram
notifier, replay-guard semantics). Instead extracted a module-level
helper `record_signature_history(db_or_conn, ...)` in
`backend/services/signature_service.py` and called it from each path:

* `/api/signatures/{id}/sign` — `SignatureService.sign_transaction` /
  `reject_transaction` now use the helper (replaces the inline INSERT).
* `/api/transactions/batch-sign` — `TransactionService.sign_transaction`
  appends after success. `request_id` threaded through the route handler
  so the whole batch shares one X-Request-Id (correct UX: one human
  action against N txs).
* `/v1/transactions/{id}/sign` — `merchant_tx_service.sign_transaction`
  appends with the merchant's per-org EC as `signer_address`.
  `request_id` plumbed through `routes_public_v1.py`.

Helper is type-permissive (accepts both `AsyncDatabase` wrapper and a
bare `asyncpg.Connection`) so the merchant path doesn't have to
round-trip through the wrapper just for one row.

Audit-misses are non-fatal: `UniqueViolationError` is the only branch
that re-raises (caller decides 409 vs no-op); anything else is logged
and the sign succeeds anyway. Sign correctness takes precedence over
audit completeness when the alternative is a failed merchant API call.

Tests: `test_signature_history_helper.py` (4 cases — wrapper kwargs,
asyncpg positional, strict-wrapper fallback, unique-violation
propagation). Existing `test_signature_service.py` updated to match
the new tx_payload kwarg from the Wave-22 scaffold.

### TD-3. KMS / Vault signer backends never run against real provider

`backend/safina/signer_backends.py` ships `KMSSignerBackend` and
`VaultSignerBackend` as stubs. Unit tests pass them through an
in-process fake, but no integration test exercises a real AWS KMS
or HashiCorp Vault Transit engine. The day we flip
`ORGON_SIGNER_BACKEND=kms` in prod, that is the first execution.

**Fix:** dedicated terraform-managed KMS key in a sandbox AWS account,
a CI job that wires up `aws-vault` (or OIDC role) and runs a focused
suite against it on every change to `safina/`.

**Why not yet:** infra-procurement gate, not code gate. Tracked
separately on the SOC 2 trail.

---

## L2 — trust-degrading

### TD-4. ~~`JwtAuditMiddleware` added twice in `backend/main.py`~~ — **FIXED 2026-05-19**

Prod analysis of the last 24h of `audit_log` showed **21 pair-buckets vs
2 singles** at second-granularity. Duplicate confirmed. Second
`app.add_middleware(JwtAuditMiddleware)` removed. After redeploy
expect pair-count to drop to zero on new rows; existing duplicate
rows stay (audit_log is append-only by trigger — `DELETE` blocked
intentionally).

### TD-5. ~~`backend/tests/test_compliance.py` ImportError~~ — **PARTIALLY FIXED 2026-05-19**

Collection no longer crashes. Bad `from backend.database.pool import
get_pool` replaced with `asyncpg.create_pool(os.environ["DATABASE_URL"])`,
whole module gated by `pytest.mark.skipif(no DATABASE_URL)`. CI now
runs `pytest backend/tests/` without `--ignore` and gets clean
collection.

**Still TODO:** the 12 collected tests use bare `async def` fixtures
without `@pytest_asyncio.fixture` — they fail with
"coroutine 'pool' was never awaited" even when a real Postgres is
attached. A real rewrite — model the suite on `test_aml_alerts.py` /
`test_idempotency.py` fake-pool unit tests — is still pending.

### TD-6. `transaction_monitoring_rules` evaluation order is undefined

Active rules are scanned in DB return order; verdict picks the
strictest action. For two `block` rules from two different orgs
(global + own), the alert is recorded against the rule that happens
to come first. Operators reading the AML queue can't tell which
rule triggered first.

**Fix:** add `priority int DEFAULT 0` to `transaction_monitoring_rules`,
`ORDER BY priority ASC, id ASC` in the evaluator. Migration is
trivial; risk is purely cosmetic.

**Why not in E-07:** scope creep. E-07 was about new rule kinds +
scope, not deterministic ordering.

### TD-7. `recipient_geo_block` is a documented stub

Added in E-07. Returns `False` always, logs once per process. A
rule of this type is creatable in the admin UI, will look
configured, and will NEVER fire.

**Fix:** part of E-09 (Travel Rule). Pick a geo provider
(MaxMind GeoIP2 ASN-based, or Sumsub Travel Rule which already
gates KYC). Wire `_check_recipient_geo_block_stub` →
`_check_recipient_geo_block` against it. Add a CI guard that fails
if anyone makes a rule of type `recipient_geo_block` while the
stub flag is on.

### TD-8. ~~Overlay migrations 027–046 don't write `schema_migrations`~~ — **FIXED 2026-05-19**

`052_backfill_schema_migrations.sql` inserts the missing markers
in one idempotent statement. Applied to prod via `psql`. Verified:
`schema_migrations` now lists 28 rows (025–052 plus 000 canonical).

**Still TODO:** add a CI lint that fails if any new overlay file
lacks an `INSERT INTO schema_migrations` final statement. Phase 1's
047–051 all do this correctly; the lint catches future drift.

---

## L3 — friction

### TD-9. ~~CSV export reads details from text column inconsistently~~ — **FIXED 2026-05-19**

Extracted `_normalize_details(value) -> dict | list` in
`routes_audit.py`. Both `_serialize_row` and the CSV streamer now
share it. 14 unit tests on the serializer stay green.

### TD-10. Pydantic v1 deprecation warnings

Test runs print:
```
PydanticDeprecatedSince20: Support for class-based `config` is
deprecated, use ConfigDict instead.
```

Three occurrences. Doesn't break anything; suite stays green. But
warnings turn to errors in Pydantic v3, and we'll be migrating
under time pressure.

**Fix:** grep `class Config:` in pydantic model files, replace with
`model_config = ConfigDict(...)`. One PR.

### TD-11. ~~Sidebar nav `/compliance` mis-flagged as roadmap~~ — **PARTIALLY FIXED 2026-05-19**

Promoted `/compliance/rules` (Wave 23+25) and `/compliance/reviews`
(AML queue, Wave 23+26) into the "insights" group as production-ready
entries. Index `/compliance` stays in roadmap until a real dashboard
lives there. i18n keys added to ru/en/ky.

**Still TODO:** if/when a `/compliance/sar` route surfaces, add it
alongside the other two. Today the SAR pipeline (Wave 24) is invoked
through compliance-officer flows inside `/compliance/reviews`, not a
dedicated page.

### TD-12. Inline-emit webhooks lack payload-pinning tests

Three live webhook emits sit **inline** inside large polling functions:
* `transaction.broadcasted` + `transaction.confirmed` — inside
  `transaction_service.sync_transactions` (~100 LOC body).
* `wallet.activated` — inside `wallet_service.sync_wallets` (~120 LOC body).

The three cleanly-isolated emits (`wallet.deposit.detected`,
`policy.triggered`, `user.created`) got full payload-pinning tests
in Wave 30 — Postgres `xmax = 0` discriminator and ON CONFLICT
semantics covered. The three inline-emit ones don't, because
exercising the conditional in isolation requires mocking a Safina
client + iterator + DB schema fixtures, which is more scaffolding
than test.

**Risk:** L2. The emits do fire correctly in prod (verified live);
the gap is regression-only. If a future edit to the surrounding sync
logic accidentally breaks a gate (e.g. changes the
`prev_row.tx_hash` emptiness check or `not prev_addr and addr` check),
nothing in the test suite would notice until the asystem-core
integration starts showing missing webhooks.

**Fix:** extract each emit block to a private helper —
`_emit_tx_lifecycle_events(pool, prev_row, tx, wallet_name)` and
`_emit_wallet_activated_if_address_appeared(pool, existing, w, addr)`
— and test the helpers directly with the fake-pool pattern in
`backend/tests/test_user_created_event.py`. ~1h refactor + 2h tests.
Deferred from Wave 30 to avoid touching live polling paths in the
same sprint as the contract changes.

### TD-13. `wallet.deposit.pending` event for mempool-stage signal

Surfaced by the end-user customer-dev walkthrough
(`docs/CUSTDEV_OPERATOR_END_USER.md` EU-4). User-pain: when an
end-user sends crypto to a deposit address, there's a 30s-15min gap
between "tx broadcast" and "first confirmation". During that window
the operator UI shows `awaiting_payment` with no indication that we
*do* see the tx — and no signal to ourselves either, because all
three deposit sources hard-code `only_confirmed=true`:

* `backend/services/deposit_sources/tron.py:39,77` — `"only_confirmed": "true"`
* `backend/services/deposit_sources/bitcoin.py:27` — `if not status.get("confirmed"): continue`
* `backend/services/deposit_sources/ethereum.py` — Etherscan default behaviour returns confirmed txs

A `wallet.deposit.pending` event firing at mempool-detection would
let asystem-core show "we see your transaction, waiting for X
confirmations" and proactively notify the user instead of letting
them assume the deposit was lost.

**Why this is L2, not L1:** the absence is observability, not
correctness. Confirmed-only path is conservative-safe (no
false-positives from dropped mempool txs, no double-spend confusion).
The bug we'd be fixing is "user anxiety", not "lost money".

**Fix (when prioritised, est. 1-2 days):**
1. Add a separate `scan_mempool(client, w, since)` method to the
   `DepositSource` protocol that's optional (default returns []).
2. Implement for Tron (TronGrid has `confirmed=false` queries via
   `events_unconfirmed` table; Bitcoin via mempool.space API; ETH
   via Etherscan's `txlistinternal` or Alchemy WebSocket pending pool).
3. Persist mempool-stage rows to a NEW `deposits_pending` table
   (NOT `deposits` — those are confirmed only, can't break that
   contract). Promote to `deposits` when sync sees same tx_hash
   confirmed; expire from `deposits_pending` after N hours if never
   confirmed (probable mempool drop).
4. Emit `wallet.deposit.pending` from the mempool-side path; keep
   `wallet.deposit.detected` from the confirmed-side (current
   contract preserved).
5. Document mempool-drop semantics — `pending` emitted, then no
   `detected` follow-up = tx was dropped/replaced. asystem-core
   handler should NOT auto-flip order to `paid` on pending; only
   show informative UI.

**Why not now:** false-positive risk profile vs UX gain — best done
after at least one live ORGON-via-asystem-core operator complains
about the gap. Don't add explorer-API quota cost (mempool queries
are usually rate-limited harder than confirmed) speculatively.

---

## Process notes

* This file lives in `docs/` so it ships with the repo and is
  visible to every new contributor without needing tribal knowledge.
* Adding a `TD-N` entry is **not free** — readers count entries
  as a signal of organizational health. Keep this list tight: only
  things a future engineer would honestly want to know about
  before touching the area.
* Numbering is append-only — never recycle a TD-N slot. When a
  TD-N is fixed, delete the entry but the number stays retired so
  references in commit messages stay readable.
