# Deployment

How ORGON gets from a `git push` to a live container, and how to recover
when something breaks.

---

## Topology

| App | Branch | Domain | Internal port |
|---|---|---|---|
| `orgon-frontend` | `main` | `https://<prod-domain>` | 3000 |
| `orgon-backend` | `main` | `https://<prod-api-domain>` | 8890 |
| `orgon-preview-frontend` | `preview-ready` | `https://<preview-domain>` | 3000 |
| `orgon-preview-backend` | `preview-ready` | `https://<preview-api-domain>` | 8890 |
| `orgon-pg-prod` | — | (internal, Coolify network) | 5432 |
| `orgon-pg-preview` | — | (internal, Coolify network) | 5432 |

Concrete domains and Coolify UUIDs are filled in once the new server is
provisioned. Update this table with the actual values — don't leave
placeholders in production.

Coolify UI: `https://<coolify-host>` (auth as configured per host).
API token: store at `~/.config/orgon/coolify-token` with mode `0600`.

DB: per-environment Postgres in Coolify (no shared container — each
env owns its own). Demo migrations are idempotent and isolated to
`Demo Exchange KG` / `Demo Broker KG` orgs.

---

## Trigger a deploy

```bash
TOKEN=$(cat ~/.config/orgon/coolify-token)

# Frontend (replace <APP_UUID> with the one from Coolify UI)
curl -X GET -H "Authorization: Bearer $TOKEN" \
  "https://<coolify-host>/api/v1/deploy?uuid=<APP_UUID>"
```

Coolify builds the container from `git pull origin <branch>` + `docker build`.
A Next.js full build is ~3–5 minutes; a Python build is ~1–2 minutes (most
of which is `pip install`).

GitHub Actions triggers Coolify automatically on green CI for `main` and
`preview-ready` — see [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
and [`CI-CD.md`](CI-CD.md). The manual `curl` above stays useful for
out-of-band redeploys and for branches outside the deploy mapping.

---

## Watch a deploy

```bash
# Container status (run on the Coolify host)
ssh <coolify-host> 'docker ps --filter name=<APP_UUID> --format "{{.Status}} | {{.Image}}"'

# Live logs
ssh <coolify-host> 'docker logs -f $(docker ps --filter name=<APP_UUID> -q)'

# Coolify deployment record
curl -sS -H "Authorization: Bearer $TOKEN" \
  "https://<coolify-host>/api/v1/deployments/<deployment_uuid>"
```

If a deploy stalls or fails, the build container leaves logs accessible via
Coolify UI → Application → Deployments → individual deployment.

---

## Required environment variables

These MUST be set in Coolify per environment. Auto-generated fallbacks
(where they exist) are fine for ephemeral CI but unsafe in prod — they
rotate on container restart and silently invalidate live tokens.

| Var | Required for | Notes |
|---|---|---|
| `DATABASE_URL` | always | `postgresql://user:pw@host:port/db` — points at the per-env Postgres provisioned in Coolify |
| `JWT_SECRET_KEY` | always | 32+ bytes random hex (`openssl rand -hex 32`). **Don't rely on the auto-generated default** — every restart kicks every user back to login. |
| `SAFINA_BASE_URL` | always | `https://my.safina.pro/ece/` for prod Safina, partner-issued for staging |
| `SAFINA_EC_PRIVATE_KEY` | env-backend signer | EC SECP256k1 private key (hex). Required when `ORGON_SIGNER_BACKEND=env` (default). Stored in Coolify env, not in repo. **For institutional production: switch to `kms` or `vault` backend** — see `backend/safina/signer_backends.py`. |
| `ORGON_SIGNER_BACKEND` | optional | `env` (default) / `kms` / `vault`. KMS and vault are stubs until wired — see `signer_backends.py` for setup checklists. |
| `AWS_KMS_KEY_ID` / `AWS_REGION` | only if signer=kms | KMS key arn or alias and region (default `eu-central-1`). Backend role must have `kms:Sign` + `kms:GetPublicKey`. |
| `VAULT_ADDR` / `VAULT_KEY_NAME` / `VAULT_TOKEN` | only if signer=vault | Vault Transit engine endpoint, key name (default `safina-ec`), and access token. |
| `SENTRY_DSN` | recommended | enables error tracking via `backend/observability.py`. Empty = no Sentry, JSON logs still work. |
| `ORGON_JSON_LOGS` | recommended | `1` to switch logger to structured JSON (better for log shippers). Default plain text. |
| `STRIPE_API_KEY` | only if billing enabled | `sk_test_…` / `sk_live_…`. Empty → billing routes return 503, not crash. |
| `STRIPE_WEBHOOK_SECRET` | only if billing enabled | `whsec_…` from Stripe dashboard webhook. Required for `/api/v1/billing/webhook` to actually dispatch events. |
| `STRIPE_PRICE_STARTER` / `_BASIC` / `_PRO` | only if billing enabled | one Stripe Price ID per plan slug. Append `_YEARLY` for yearly counterparts. |
| `ORGON_PUBLIC_URL` | only if billing enabled | base URL for Stripe success/cancel redirects, e.g. `https://orgon.asystem.kg` |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | only if email enabled | empty → email_service falls back to file backend (writes to `/tmp/orgon_emails/`), useful for dev. |
| `ORGON_PARTNER_REPLAY_OFF` | never in prod | dev escape hatch to skip HMAC nonce dedup for replay-testing. |
| `ORGON_AUTO_MIGRATE` | greenfield deploys | Set to `1` so the container's entrypoint applies `000_canonical_schema.sql` on first boot (only if marker absent — safe to leave on across restarts). Leave unset on existing DBs to avoid accidental application. |

Verify after deploy: `curl -sS https://orgon-api.asystem.kg/api/health`
should return `{"ok": true, ...}` with no 5xx in the logs for the first
30s. If JWT auth fails immediately for everyone, the secret was missed.

---

## Apply a database migration

Schema lives in **two layers**:

1. **`backend/migrations/000_canonical_schema.sql`** — single canonical
   snapshot that replaces the pre-Wave-11 47-file chain. Applied **once**
   on a fresh DB. Re-runs are gated by the `schema_migrations` row
   `version='000_canonical_schema'` inserted at the bottom of the file.
2. **`backend/migrations/0NN_*.sql`** (`025+` going forward) — idempotent
   overlay migrations applied in numeric order on top of the canonical.
   Each MUST `INSERT INTO schema_migrations (version, …) ON CONFLICT DO
   NOTHING` so re-runs no-op.

### Greenfield (new server, no DB yet)

The cleanest path: set `ORGON_AUTO_MIGRATE=1` in Coolify env. Container
entrypoint reads `DATABASE_URL`, checks for the canonical marker, applies
`000_canonical_schema.sql` if absent, then any post-canonical overlay
migrations in numeric order. Idempotent across restarts.

Manual fallback (e.g. running locally against an empty DB):

```bash
psql -v ON_ERROR_STOP=1 \
  "$DATABASE_URL" \
  -f backend/migrations/000_canonical_schema.sql

# then any 025+ overlay migrations in order:
for f in backend/migrations/0*.sql; do
  case "$f" in *000_canonical*) continue ;; esac
  psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f "$f"
done
```

### Adding a new migration

1. Pick the next free number (`025_`, `026_` …) under `backend/migrations/`.
2. Write idempotent SQL: `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF
   NOT EXISTS`, `DO $$ … END $$` for triggers/policies, `ON CONFLICT
   DO NOTHING` for any seed inserts. Wrap in `BEGIN; … COMMIT;`.
3. Append the tracking row at the bottom:
   ```sql
   INSERT INTO public.schema_migrations (version, description)
   VALUES ('025_my_change', 'one-line summary')
   ON CONFLICT (version) DO NOTHING;
   ```
4. Verify locally on a fresh Postgres → app startup → `/api/health=200`.
5. Open PR. CI's `fresh-install` job replays the full chain on a clean
   DB and asserts `/api/health` answers within 30s.

### Applying a single migration to a running production DB

```bash
# Copy the new migration into the running backend container, apply via
# its asyncpg pool. The endpoint also supports remote application
# (POST /api/health/run-migrations, super_admin only).
scp backend/migrations/025_my_change.sql <coolify-host>:/tmp/
ssh <coolify-host> 'BE=$(docker ps --filter name=<backend-uuid> -q); \
  docker cp /tmp/025_my_change.sql $BE:/tmp/m.sql; \
  docker exec $BE psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f /tmp/m.sql'
```

For destructive migrations: prefix with a `pg_dump` to a host folder.
For RLS / trigger migrations: dry-run first by replacing `COMMIT;`
with `ROLLBACK;`.

`POST /api/health/run-migrations` (super_admin only) applies the same
canonical-then-overlay sequence the entrypoint does. It is
admin-gated since this branch.

---

## Rollback

Coolify keeps previous Docker images. Quickest rollback:

```bash
# 1. On the Coolify host, list previous good image tags
ssh <coolify-host> 'docker images | grep <APP_UUID> | head -5'

# 2. From Coolify UI: Deployments → pick the last green one → "Rollback".
#    This is preferred over manual docker run — Coolify re-attaches the
#    network, env vars, and volumes correctly.
```

For a clean rollback to a specific commit: in the Coolify app config,
temporarily set `git_commit_sha` to the target SHA, then trigger
`/deploy`. Reset to `auto` once the rollback is verified.

For DB schema rollback: future `0NN_*.sql` migrations should ship with
either an explicit revert path inside the same migration (e.g.
`DROP IF EXISTS` matching the new objects) or a paired
`0NN_xxx_revert.sql`. Backups (see § Backups) are the ultimate
fallback for irreversible data changes.

---

## Common breakages

| Symptom | Cause | Fix |
|---|---|---|
| Coolify API returns `522` / 5xx | Coolify host overloaded (often during a heavy build) | wait 30–60s and retry; check the Coolify host itself |
| Deploy build fails on `npm install` | new dep conflict with Tailwind 4 | use `--legacy-peer-deps` in Dockerfile RUN, or pin the offending dep |
| Container in `running:unhealthy` | healthcheck path requires auth or returned 500 | check the healthcheck command in Coolify; ensure it hits `/api/health` (no auth) |
| Login starts returning 401 unexpectedly | `JWT_SECRET_KEY` env regenerated mid-flight (auto-fallback in `backend/config.py`) | set `JWT_SECRET_KEY` explicitly in Coolify env, redeploy |
| Frontend shows "Failed to fetch" | wrong `NEXT_PUBLIC_API_URL` or browser CORS block | verify env in Coolify FE app, hit `/api/v1/billing/plans` from terminal |
| Backend container restarts on boot, logs show `relation "users" does not exist` | `ORGON_AUTO_MIGRATE=1` not set on a virgin DB, OR `DATABASE_URL` points at an empty DB and auto-migrate didn't run | set the env, redeploy. Or apply canonical manually: see § Apply a database migration. |
| `entrypoint.sh` line about applying canonical printed and then container hangs | the connecting role doesn't own the `public` schema | `GRANT ALL ON SCHEMA public TO <orgon_user>` in psql as the postgres super-user, then redeploy |

---

## Backups

The repo ships [`scripts/backup_pg.sh`](scripts/backup_pg.sh) — `pg_dump`
piped through gzip, with mtime-based local retention **and optional
off-site S3-compatible upload** (works with AWS S3, Cloudflare R2, Wasabi,
or any MinIO-style endpoint).

Default behaviour: `/var/backups/orgon/orgon-<utc-timestamp>.sql.gz`,
retain 14 days, refuse to keep dumps under 4 KiB (so a partial run can't
silently age out the good copies).

### Local-only (matches the old behaviour)

```bash
DATABASE_URL=postgresql://orgon:…@host/orgon_db \
  ./scripts/backup_pg.sh
```

### With off-site mirror (recommended for prod)

```bash
DATABASE_URL=postgresql://orgon:…@host/orgon_db \
ORGON_BACKUP_S3_BUCKET=s3://orgon-backups \
AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=… \
AWS_ENDPOINT_URL_S3=https://<account>.r2.cloudflarestorage.com \
  ./scripts/backup_pg.sh
```

Each upload is verified via `aws s3api head-object` — the script exits
non-zero if remote size diverges from local. Pair with R2/S3 lifecycle
rules for off-site retention (don't manage that here, otherwise a
single host compromise can wipe history).

### systemd timer (cron-equivalent on the host)

```ini
# /etc/systemd/system/orgon-backup.service
[Service]
Type=oneshot
EnvironmentFile=/etc/orgon/backup.env       # holds DATABASE_URL + S3 creds (mode 0600)
ExecStart=/opt/orgon/scripts/backup_pg.sh

# /etc/systemd/system/orgon-backup.timer
[Timer]
OnCalendar=*-*-* 03:00:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
```

`systemctl enable --now orgon-backup.timer`, then verify
`journalctl -u orgon-backup.service -n 50` after the next firing.

### Manual one-off

```bash
docker exec <coolify-postgres-container> pg_dump -U <user> -F c <db> \
  | gzip -9 > "/tmp/orgon-$(date +%Y%m%dT%H%M%SZ).sql.gz"
```
