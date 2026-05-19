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

### TD-1. `audit_log` has no `organization_id`

Discovered while wiring E-04 (`/api/audit/events`). The canonical
`audit_log` table predates multi-tenancy and has no `organization_id`
column — every tenant's audit rows live in one undifferentiated
heap. Today this is masked by RBAC: only `platform_admin` /
`company_admin` / `company_auditor` can hit `/api/audit/*`, and a
compliance officer querying for "events on my org" is implicitly
trusted to filter by `details.partner_id` or scan via the resource
type.

If a SaaS-tier merchant ever calls audit endpoints (which they will,
once we surface them in `/v1/*`), this design leaks every other
merchant's actions.

**Fix:** new migration that
  1. `ALTER TABLE audit_log ADD COLUMN organization_id uuid` (nullable).
  2. Backfill from `details->>'partner_id'` and via `JOIN users` for
     rows where `user_id` resolves to a single org.
  3. `DROP TRIGGER` (append-only) only for the duration of the
     backfill, then re-create. (The trigger blocks even our own
     UPDATEs.)
  4. Enable RLS on `audit_log` analogous to `wallets` / `transactions`.

**Why not in E-04:** trigger drop + bulk UPDATE on a multi-million-row
table is exactly the operation memory `feedback_no_rapid_deploys` and
the "retire 039's destructive bulk-tombstone UPDATE" commit warn
against. Wants its own change-window, its own communication.

Acknowledged in `routes_audit.py` module docstring.

### TD-2. `signature_history` not populated for `/v1/*` sign + batch-sign

Discovered while wiring E-02 (`signature_history.request_id`).

* `/v1/transactions/{id}/sign` calls `merchant_tx_service.sign_transaction`
  which goes **straight into Safina** — no `signature_history` row.
* `/api/transactions/batch-sign` calls `TransactionService.sign_transaction`
  which only updates `transactions.status` — no `signature_history` row.

Only `/api/signatures/{id}/sign` (via `SignatureService`) writes a
row. So our append-only audit of multi-sig actions is partial.

**Fix:** thread `SignatureService.sign_transaction` (which already
writes `signature_history`) under both other callers. Drop the
`TransactionService.sign_transaction` shortcut, replace its single
caller (`/batch-sign`) with the SignatureService method in a loop.

**Why not in E-02:** scope creep. E-02 was about *threading the
request-id*, not unifying three sign paths. Surfaced honestly in
the E-02 summary.

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
