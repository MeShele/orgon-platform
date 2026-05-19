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

### TD-4. `JwtAuditMiddleware` added **twice** in `backend/main.py`

```python
# backend/main.py
app.add_middleware(JwtAuditMiddleware)  # line 549
app.add_middleware(JwtAuditMiddleware)  # line 553 — duplicate
```

Comments on both occurrences are nearly identical. Either:
  (a) The second was a merge slip and we now log every dashboard
      mutation TWICE into `audit_log`. (Likely. Need to grep prod
      logs for paired rows on the same `(user_id, action, created_at)`
      tuple to confirm.)
  (b) The original intent was two configurations of the middleware
      (one for `/api/`, one for `/api/v1/`) and the configuration
      diff got lost during a refactor.

**Fix:** dump 24h of prod `audit_log` rows grouped by
`(user_id, action, resource_type, date_trunc('second', created_at))`;
if pair-counts are ~2 across the board, drop the second `add_middleware`
call and verify the count halves on next deploy.

**Why not in Phase 1:** I spotted it during the E-02 audit but it's
unrelated to any of the five epics. Doing it in the Phase 1 commit
would have muddied the diff and made rollback grainy.

### TD-5. `backend/tests/test_compliance.py` ImportError

```
backend/tests/test_compliance.py:7: in <module>
    from backend.database.pool import get_pool
E   ModuleNotFoundError: No module named 'backend.database.pool'
```

`backend/database/pool.py` does not exist — the directory has
`db.py`, `db_postgres.py`, `db_hybrid.py`, `migrations.py`. CI
explicitly excludes this file via `--ignore`, so it goes silent.

This existed on `main` before any of my work. The test file is
quoting Compliance Service API patterns that are still relevant —
deleting it loses signal.

**Fix:** rewrite the imports to use `backend.services.compliance_service`
and the AsyncDatabase pool fixture pattern used by `test_aml_alerts.py`.
2–3 hours.

**Why not now:** outside Phase 1 / E-07 scope. Could be a clean tech-
debt PR.

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

### TD-8. `prefer-existing-overlay` vs `IF NOT EXISTS` discipline

Migrations 027–046 (pre-Phase-1) do not write into
`schema_migrations`. The README says they MUST. The entrypoint
loader applies them on every boot because they're not gated.

This is fine while every overlay is idempotent. It becomes a
problem the day someone writes a non-idempotent overlay and trusts
the loader to skip it.

**Fix:** retro-add `INSERT INTO schema_migrations VALUES (...)` to
each 027–046 migration in a single chore PR. Then add a CI lint
that fails if any new overlay lacks the marker. Phase 1's 047–051
all do this correctly.

**Why not now:** retro-edits to applied migrations are sketchy
(the entrypoint won't re-apply them, so the new `INSERT` would
never run on existing installs). Better fix: introduce a one-off
`100_backfill_schema_migrations.sql` that lists everything
pre-Phase-1.

---

## L3 — friction

### TD-9. CSV export reads details from text column inconsistently

`audit_log.details` is `jsonb`. asyncpg returns it as `dict` (or
sometimes `str` after a round-trip via fetch + insert). The serializer
in `routes_audit.py:_serialize_row` and the CSV streamer
in `routes_audit.py:export_audit_events_csv` both handle both shapes.
Same logic appears in two places.

**Fix:** extract `_normalize_details(value) -> dict` and call from both.
20-line refactor.

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

### TD-11. `frontend/src/components/layout/sidebar-nav.ts` has 4 "roadmap" entries that aren't real

`/compliance`, `/users`, `/documents`, `/settings` are flagged
`roadmap: true` in the sidebar. The "Скоро" badge sells breadth to
demo viewers but customers actually click these and see the in-
development banners.

`/compliance` is no longer roadmap — Wave 25 made `/compliance/rules`
a real flow. Keeping the parent flagged misleads operators.

**Fix:** split the entry into:
* `/compliance/rules` — production-ready
* `/compliance/alerts` — production-ready (AML queue)
* `/compliance/sar` — production-ready (Wave 24)
* leave `/compliance` (the index page) as `roadmap` until we build
  a real dashboard at that route.

**Why not now:** purely a frontend polish task; we're on the backend
hardening sprint.

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
