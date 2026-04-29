# Historical migrations — DO NOT RUN

These files are the migration journey that produced the schema
captured in `../000_canonical_schema.sql`. They are preserved for git
history, archeology, and migration provenance. **Nothing in here is
applied to fresh installs anymore.**

---

## What lives where

| Subdir | Origin path before consolidation | Contents |
|---|---|---|
| `overlay/` | `backend/migrations/{000..024}*.sql` + helper scripts | 28 migration files + 4 helper scripts (`apply_*.sh`, `*_rls_test.sql`) |
| `legacy_db_migrations/` | `backend/database/migrations/*.sql` | 18 files, the older legacy chain |

Total: 46 migration files + 4 scripts collapsed into one canonical.

---

## Why this was necessary

The pre-consolidation chain had **silent failures masked by
`ON_ERROR_STOP=0`**:

- **Two mutually-exclusive `000_*.sql` files** in the overlay dir
  (`000_base_schema.sql` and `000_init_uuid_base.sql`); CI explicitly
  skipped both via `grep -vE '/000_'`.
- **Three `006_*.sql` files** creating overlapping billing tables
  (`006_billing_system.sql`, `006_billing_system_rls_fix.sql`,
  `006_create_billing_tables.sql`).
- **FK ordering bugs:** legacy `001_wallets_transactions.sql` FKed
  into `organizations(id)` and `users(id)` before either table was
  created in CI's apply order.
- **Wrong column FK:** legacy `009_webhooks.sql` referenced
  `partners(partner_id)` but the actual column on `partners` is `id`
  — three webhook-related tables failed to create as a result.
- **Schema drift:** legacy chain produced `transactions.tx_unid`
  AND `transactions.unid`; UUID chain produced only `unid`. Code
  reads `unid`. Demo seed `013_demo_data.sql` originally inserted
  into `tx_unid` (and was fixed in Wave 10).

CI tests passed despite all of this because they used AsyncMock rather
than a real DB. A fresh install only got ~50% of the intended schema.

---

## If you need to consult an old migration

The files are intact. `git log --follow` on each shows authorship and
the commit context where it was added. Use them for forensic reading,
not for execution.

---

## Re-applying any of these

You should never need to. If you find yourself wanting to, the answer
is almost always "regenerate `000_canonical_schema.sql` from the most
authoritative live DB you have" rather than try to replay this chain.

If you absolutely must run an individual file (e.g., to extract a
specific function definition or RLS policy that didn't make it into
the canonical), copy it out, vet it, and run manually with
`ON_ERROR_STOP=1` against an isolated test DB. Never against prod.
