# ORGON Database Migrations

Single canonical schema file + idempotent overlay migrations for any
post-snapshot changes. The journey of how the schema got here is
preserved under `_historical/` for reference but is no longer applied.

---

## Layout

```
backend/migrations/
├── 000_canonical_schema.sql       ← apply ONCE on a fresh DB
├── 025_*.sql, 026_*.sql, ...      ← future migrations, all idempotent
├── seed_test_organizations.sql    ← e2e test fixture (NOT a migration)
├── README.md                      ← this file
└── _historical/                   ← do NOT run these on fresh installs
    ├── overlay/                   ← old backend/migrations/{000..024}*.sql
    └── legacy_db_migrations/      ← old backend/database/migrations/*.sql
```

---

## Apply on a fresh database

```bash
psql -v ON_ERROR_STOP=1 \
     -h <host> -U <user> -d <db> \
     -f backend/migrations/000_canonical_schema.sql
```

The canonical file installs:
- 60 tables (incl. `schema_migrations` tracking)
- 15 application functions + 36 triggers + 7 RLS policies
- 311 indexes
- Two extensions: `pgcrypto`, `uuid-ossp`

It is **not idempotent** — pg_dump emits bare `CREATE TABLE foo(...)`
without `IF NOT EXISTS` for everything. Apply once on a virgin DB; the
`schema_migrations` row inserted at the end (`version =
'000_canonical_schema'`) is the marker that lets `entrypoint.sh` and
the `/api/health/run-migrations` endpoint detect "already applied" and
skip.

---

## Add a new migration (`025_*.sql` and onwards)

Future schema changes go in NEW numbered files, never edit
`000_canonical_schema.sql` in place.

Required properties for any new migration:

1. **Idempotent.** `CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO NOTHING`,
   `ALTER TABLE … ADD COLUMN IF NOT EXISTS`. A migration applied twice
   must be a no-op, not an error.
2. **Tracking row.** Append at the end:
   ```sql
   INSERT INTO public.schema_migrations (version, description)
   VALUES ('025_my_change', 'one-line summary')
   ON CONFLICT (version) DO NOTHING;
   ```
3. **Wrapped in a transaction.** Start with `BEGIN;`, end with `COMMIT;`,
   so a partial failure leaves the DB in the previous state (use
   `ON_ERROR_STOP=1` when applying).
4. **Comment header explaining WHY** (date, what code change requires
   it, what data assumptions it makes).

---

## Regenerating the canonical (rare, deliberate)

If after months of overlay-migration accumulation the chain becomes
hard to reason about, you can collapse them back into a new canonical
snapshot. Procedure:

1. Pick a freshly-migrated DB (CI's fresh-install verification job
   gives you exactly this).
2. `pg_dump --schema-only --no-owner --no-acl --no-tablespaces \
     -h … -U … <db> > /tmp/new_canonical.sql`
3. Strip the `\restrict` / `\unrestrict` lines (they're psql-17
   client-only):
   `grep -vE '^\\(restrict|unrestrict)' /tmp/new_canonical.sql > /tmp/clean.sql`
4. Replace the file body of `000_canonical_schema.sql` (preserve the
   header comment block + the trailing `schema_migrations` addendum).
5. Move the consolidated overlay migrations under `_historical/overlay/`.
6. Verify on a fresh Postgres → diff = empty (modulo CHECK constraint
   cosmetic rewrites).
7. PR with detailed description.

This is a deliberate, reviewed operation — not something to do casually.

---

## Why we did this once already

Pre-consolidation we had **47 migration files in two directories**
(`backend/migrations/` and `backend/database/migrations/`) applied by CI
with `ON_ERROR_STOP=0`, swallowing FK ordering bugs, broken column refs
(`partners.partner_id` doesn't exist; column is `id`), three competing
`006_*.sql` billing files, and two mutually-exclusive `000_*.sql` base
schemas. Result: a fresh CI install only got ~50% of the intended
schema, but the test suite still went green because it used AsyncMock
mocks rather than a real DB.

The canonical file represents the schema as it actually works on
local-dev (verified end-to-end with backend code Wave 1-10). Everything
under `_historical/` is preserved as the reference for "how we got
here" but is no longer the source of truth.

See `_historical/README.md` for which files were consolidated.
