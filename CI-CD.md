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

- **`ci.yml`** runs on every push and PR to `main` / `preview-ready`.
  Jobs: `backend` (compile + migrations + pytest), `frontend` (tsc + lint
  + build), `e2e` (Playwright chromium).
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

| Secret                              | What it is                                               |
|-------------------------------------|----------------------------------------------------------|
| `COOLIFY_HOOK_PROD_FRONTEND`        | Coolify deploy URL for `orgon-frontend` (prod)           |
| `COOLIFY_HOOK_PROD_BACKEND`         | Coolify deploy URL for `orgon-backend` (prod)            |
| `COOLIFY_HOOK_PREVIEW_FRONTEND`     | Coolify deploy URL for `orgon-preview-frontend`          |
| `COOLIFY_HOOK_PREVIEW_BACKEND`      | Coolify deploy URL for `orgon-preview-backend`           |
| `COOLIFY_TOKEN`                     | Bearer token (Coolify → Profile → API tokens)            |

To get a deploy URL: Coolify UI → app → **Webhooks → Manual deploy**.
The format is `https://c.asystem.kg/api/v1/deploy?uuid=<APP_UUID>&force=false`.
Each token is per-app and per-tenant — never reuse across apps.

---

## Database topology

Today both `orgon-*` and `orgon-preview-*` apps point at the same shared
Coolify Postgres container. That's a known compromise — preview migrations
run against the same data as prod. **This is on the Sprint 5 punch list to
fix.** Recipe:

1. In Coolify, **Resources → New → Postgres 16**, name it
   `orgon-preview-pg`. Allocate it 2 GiB / 1 vCPU.
2. Copy the generated `DATABASE_URL` from its Service tab.
3. Edit the two preview apps (`orgon-preview-frontend`,
   `orgon-preview-backend`) → **Environment Variables** → set
   `DATABASE_URL` to the new value. Save.
4. Trigger a deploy of `orgon-preview-backend` so it picks up the new
   DSN — first boot will create the schema via the migrations runner
   that lives in `backend/migrations/apply_migrations.sh`.
5. Reseed the demo data:
   ```bash
   ssh suymunkul@hetzner-ax41 'sudo ssh root@10.30.30.132 \
     "docker exec -i orgon-preview-pg psql -U \$POSTGRES_USER -d \$POSTGRES_DB" \
     < backend/migrations/013_demo_data.sql'
   ```

Until that's done, treat the preview environment as having read access to
prod's data — don't run migrations against preview that you wouldn't run
against prod.

---

## Backups

Script: [`scripts/backup_pg.sh`](./scripts/backup_pg.sh) — `pg_dump` →
gzip → rotate by mtime. Designed to run from the proxmox host, not from
inside a container, so it can write to a host-level volume that's
independent of the postgres LXC.

### Cron entry

On the asystem-proxmox host, as root:

```
# /etc/cron.d/orgon-pg-backup
30 2 * * *  root  DATABASE_URL=postgresql://orgon:…@10.30.30.132:5432/orgon \
                  ORGON_BACKUP_DIR=/var/backups/orgon \
                  ORGON_BACKUP_RETENTION_DAYS=14 \
                  /opt/orgon/scripts/backup_pg.sh \
                  >> /var/log/orgon-backup.log 2>&1
```

`pg_dump` must be the same major version as the server (16). Install via
`apt-get install postgresql-client-16` if missing.

### Restore

```
gunzip -c /var/backups/orgon/orgon-20260427T023000Z.sql.gz \
  | psql "$DATABASE_URL"
```

Run against an empty database — the dump uses `--no-owner --no-privileges`
so it does not assume role names match.

### Off-site copy (recommended)

Mirror the backup directory to a second host nightly:

```
50 2 * * *  root  rsync -a --delete /var/backups/orgon/ \
                  backup@hetzner-ax41:/srv/backups/orgon/
```

---

## Local commands

| What                          | Command                                              |
|-------------------------------|------------------------------------------------------|
| Backend type-check            | `python -m compileall -q backend`                    |
| Backend tests (unit)          | `pytest backend/tests/test_signature_service.py …`   |
| Frontend type-check           | `cd frontend && npm run typecheck`                   |
| Frontend lint                 | `cd frontend && npm run lint`                        |
| Frontend build                | `cd frontend && npm run build`                       |
| Playwright (against built)    | `cd frontend && npm run test:e2e`                    |
| Playwright UI mode            | `cd frontend && npm run test:e2e:ui`                 |
| Playwright vs running server  | `PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e` |

For the auth spec to actually run (`auth.spec.ts`), set
`E2E_BACKEND_URL=https://orgon-preview.asystem.kg` and ensure the demo
seed (migration 013) is applied on that environment.

---

## Failure runbook

- **CI red on `frontend.lint`** — usually a stale `eslint` warning count.
  Investigate the actual rule, do not relax `--max-warnings`.
- **CI red on `backend.migrations`** — read the psql output. SQL syntax
  failures on a fresh db usually mean a referenced table doesn't exist
  yet (migration ordering) or a duplicate object (forgot `IF NOT EXISTS`).
- **Deploy didn't fire** — check that the CI run finished green on the
  exact commit, and that the `head_branch` was `main` or `preview-ready`.
  PR-merge commits inherit the merge commit's branch, which is normally
  fine but can surprise you when a maintainer rebases.
- **Coolify webhook returned 404** — the per-app deploy URL was rotated.
  Regenerate in Coolify and update the GitHub secret.
- **Coolify 522 from the runner** — ax41 reverse-proxy is down. Either
  wait for it to come back or invoke the deploy from the proxmox host's
  internal IP using the `c.asystem.kg`-equivalent internal URL.
