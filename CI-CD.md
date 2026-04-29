# CI/CD — ORGON

What lives in this repo, what lives in Coolify / on the host, and how the
two meet. Read this before you change anything in `.github/workflows/` or
the deploy hooks.

---

## Pipeline shape

```
push / PR ──► .github/workflows/ci.yml ──► success ┐
                                                   │
                                          .github/workflows/deploy.yml
                                                   │
                                                   ▼
                                       Coolify deploy hook (curl)
                                                   │
                                                   ▼
                                  Coolify pulls from GitHub & rebuilds
```

- **`ci.yml`** runs on every push and PR to `main` / `preview-ready`. Four jobs:
  - `backend` — `compileall` + apply canonical schema against
    `postgres:16-alpine` (strict, `ON_ERROR_STOP=1`) + verify
    `schema_migrations` marker landed + 152 unit tests must pass
  - `frontend` — `tsc --noEmit` + ESLint (max 200 warnings) +
    Next.js production build
  - `fresh-install` — clean `postgres:16-alpine` → apply canonical →
    boot uvicorn → assert `/api/health=200` within 30s. Catches any
    breakage where the schema and the app code disagree.
  - `e2e` — Playwright chromium smoke (PR + main + preview-ready only)
- **`deploy.yml`** is a `workflow_run` listener. Only fires when CI is
  green, only on the two deployable branches, and `curl`s the per-app
  Coolify deploy hook. No code is shipped from the runner — Coolify
  pulls fresh from the branch.

Branch → environment mapping:

| Branch          | Environment | Coolify apps                         |
|-----------------|-------------|--------------------------------------|
| `main`          | prod        | `orgon-frontend`, `orgon-backend`    |
| `preview-ready` | preview     | `orgon-preview-frontend`, `…backend` |

Other branches: CI runs but no deploy.

---

## Required GitHub secrets

Set under **Repo → Settings → Secrets and variables → Actions**.

| Secret                          | What it is                                       |
|---------------------------------|--------------------------------------------------|
| `COOLIFY_HOOK_PROD_FRONTEND`    | Coolify deploy URL for `orgon-frontend` (prod)   |
| `COOLIFY_HOOK_PROD_BACKEND`     | Coolify deploy URL for `orgon-backend` (prod)    |
| `COOLIFY_HOOK_PREVIEW_FRONTEND` | Coolify deploy URL for `orgon-preview-frontend`  |
| `COOLIFY_HOOK_PREVIEW_BACKEND`  | Coolify deploy URL for `orgon-preview-backend`   |
| `COOLIFY_TOKEN`                 | Bearer token (Coolify → Profile → API tokens)    |

To get a deploy URL: Coolify UI → app → **Webhooks → Manual deploy**.
The format is `https://<coolify-host>/api/v1/deploy?uuid=<APP_UUID>&force=false`.
Each token is per-app and per-tenant — never reuse across apps.

---

## Database topology

Each environment has its own Postgres in Coolify (greenfield-clean —
no shared instance). The schema is bootstrapped via:

1. Set `ORGON_AUTO_MIGRATE=1` in the Coolify env block of the backend app.
2. On first boot, the container's entrypoint applies
   `backend/migrations/000_canonical_schema.sql` (60 tables, 311 indexes,
   etc.). Idempotent across restarts via the `schema_migrations` marker.
3. Future schema changes: add `backend/migrations/0NN_xxx.sql` (idempotent,
   inserts its own `schema_migrations` row). The same entrypoint applies
   it on the next deploy.

Manual fallback (e.g. running migrations from your laptop against a remote
DB): `POST /api/health/run-migrations` (super_admin only) — runs the same
canonical-then-overlay sequence.

Demo seed: `backend/migrations/seed_test_organizations.sql` (NOT a
migration, a fixture) creates the `Demo Exchange` and `Demo Broker` orgs
with three users. Apply once after the canonical lands if you want a
demoable preview environment.

---

## Backups

Script: [`scripts/backup_pg.sh`](./scripts/backup_pg.sh). `pg_dump | gzip`
with mtime-based local retention **and** optional off-site S3-compatible
upload (works with AWS S3 / Cloudflare R2 / Wasabi / MinIO).

### systemd timer (recommended on the Coolify host)

```ini
# /etc/systemd/system/orgon-backup.service
[Service]
Type=oneshot
EnvironmentFile=/etc/orgon/backup.env       # mode 0600
ExecStart=/opt/orgon/scripts/backup_pg.sh

# /etc/systemd/system/orgon-backup.timer
[Timer]
OnCalendar=*-*-* 03:00:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
```

`backup.env` content (mode 0600):

```bash
DATABASE_URL=postgresql://orgon:…@<host>:5432/orgon
ORGON_BACKUP_DIR=/var/backups/orgon
ORGON_BACKUP_RETENTION_DAYS=14

# Off-site mirror — recommended for production
ORGON_BACKUP_S3_BUCKET=s3://orgon-backups
AWS_ACCESS_KEY_ID=…
AWS_SECRET_ACCESS_KEY=…
AWS_ENDPOINT_URL_S3=https://<account-id>.r2.cloudflarestorage.com
```

`pg_dump` must be the same major version as the server (16). Install via
`apt-get install postgresql-client-16` if missing.

### Restore

```bash
gunzip -c /var/backups/orgon/orgon-20260429T030000Z.sql.gz \
  | psql "$DATABASE_URL"
```

Run against an empty database — the dump uses `--no-owner --no-privileges`
so it does not assume role names match.

For off-site retention: configure S3 lifecycle rules **on the bucket**
(don't manage them in the script — that way a host compromise can't wipe
history).

---

## Local commands

| What                          | Command                                                |
|-------------------------------|--------------------------------------------------------|
| Backend compile-check         | `.venv/bin/python -m compileall -q backend`            |
| Backend unit tests (152)      | `.venv/bin/python -m pytest backend/tests/ -v`         |
| Frontend type-check           | `cd frontend && npx tsc --noEmit`                      |
| Frontend lint                 | `cd frontend && npm run lint`                          |
| Frontend build                | `cd frontend && npm run build`                         |
| Playwright (against built)    | `cd frontend && npm run test:e2e`                      |
| Playwright UI mode            | `cd frontend && npm run test:e2e:ui`                   |
| Playwright vs running server  | `PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e` |
| Apply canonical schema (fresh)| `psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f backend/migrations/000_canonical_schema.sql` |

For the auth spec to actually run (`auth.spec.ts`), set
`E2E_BACKEND_URL=https://<api-host>` and ensure
`seed_test_organizations.sql` is applied on that environment.

---

## Failure runbook

- **CI red on `backend`** — read the psql output. With `ON_ERROR_STOP=1`
  any schema failure surfaces immediately. Most commonly: a new
  `0NN_*.sql` migration is not idempotent, or an existing table /
  trigger / policy collision.
- **CI red on `fresh-install`** — the canonical applied but
  `/api/health` didn't answer in 30s. Check the uvicorn log lines
  printed by the job. Usually one of: missing env var (e.g. forgot to
  set `JWT_SECRET_KEY`), import error in newly-added module, a service
  that requires DATABASE_URL but reads it lazily and crashes on first request.
- **CI red on `frontend.lint`** — usually a stale ESLint warning count.
  Investigate the actual rule, do not relax `--max-warnings`.
- **Deploy didn't fire** — check that the CI run finished green on the
  exact commit, and that the `head_branch` was `main` or `preview-ready`.
  PR-merge commits inherit the merge commit's branch, which is normally
  fine but can surprise you when a maintainer rebases.
- **Coolify webhook returned 404** — the per-app deploy URL was rotated.
  Regenerate in Coolify and update the GitHub secret.
- **First boot after greenfield deploy stays in 502** — the entrypoint's
  auto-migrate path crashed mid-apply. Check the container logs for the
  `psql:` line; usually `DATABASE_URL` env was wrong or the canonical
  ran into a permissions issue (the connecting user must own the
  public schema).
