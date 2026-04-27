# Deployment

How ORGON gets from a `git push` to a live container, and how to recover
when something breaks.

---

## Topology

| App | Coolify uuid | Branch | Domain | Internal port | Host port |
|---|---|---|---|---|---|
| `orgon-frontend` | `p10p6tfvyl5b86zlfizowp79` | `main` | https://orgon.asystem.kg | 3000 | 3100 |
| `orgon-backend` | `g5ktpm7dy1abguwpy4tm7dpv` | `main` | https://orgon-api.asystem.kg | 8890 | 8891 |
| `orgon-preview-frontend` | `ngsw9w49kjn2qrgchaw850jg` | `preview-ready` | https://orgon-preview.asystem.kg | 3000 | 3200 |
| `orgon-preview-backend` | `kvdb0wtgo8ysyzchbjjo7n8o` | `preview-ready` | https://orgon-preview-api.asystem.kg | 8890 | 8892 |

Coolify UI: <https://c.asystem.kg> (Authentik OIDC).
API token: store at `~/.config/orgon/coolify-token` with mode `0600`.

DB: shared `coolify-postgres` container on `asystem-proxmox` (10.30.30.132).
Both prod and preview hit it; demo migrations are idempotent and isolated
to `Demo Exchange KG` / `Demo Broker KG` orgs.

---

## Trigger a deploy

```bash
TOKEN=$(cat ~/.config/orgon/coolify-token)

# Frontend
curl -X GET -H "Authorization: Bearer $TOKEN" \
  "https://c.asystem.kg/api/v1/deploy?uuid=ngsw9w49kjn2qrgchaw850jg"

# Backend
curl -X GET -H "Authorization: Bearer $TOKEN" \
  "https://c.asystem.kg/api/v1/deploy?uuid=kvdb0wtgo8ysyzchbjjo7n8o"
```

Coolify builds the container from `git pull origin <branch>` + `docker build`.
A Next.js full build is ~3–5 minutes; a Python build is ~1–2 minutes (most
of which is `pip install`).

GitHub Actions now triggers Coolify automatically on green CI for `main`
and `preview-ready` — see [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
and [`CI-CD.md`](CI-CD.md). The manual `curl` above stays useful for
out-of-band redeploys (e.g. when the runner can't reach `c.asystem.kg`)
and for branches outside the deploy mapping.

---

## Watch a deploy

```bash
# Container status
ssh asystem-proxmox 'docker ps --filter name=ngsw9w49kjn2qrgchaw850jg --format "{{.Status}} | {{.Image}}"'

# Live logs (tail)
ssh asystem-proxmox 'docker logs -f $(docker ps --filter name=g5ktpm7dy1abguwpy4tm7dpv -q)'

# Coolify deployment record
curl -sS -H "Authorization: Bearer $TOKEN" \
  "https://c.asystem.kg/api/v1/deployments/<deployment_uuid>"
```

If a deploy stalls or fails, the build container leaves logs accessible via
Coolify UI → Application → Deployments → individual deployment.

---

## Apply a database migration

```bash
# Migrations live in backend/migrations/*.sql
# Apply via the running backend container's asyncpg connection:
scp backend/migrations/01N_xxx.sql asystem-proxmox:/tmp/
ssh asystem-proxmox 'BE=$(docker ps --filter name=g5ktpm7dy1abguwpy4tm7dpv -q); \
  docker cp /tmp/01N_xxx.sql $BE:/tmp/m.sql; \
  docker exec $BE python -c "
import asyncio, asyncpg, os
async def main():
  conn = await asyncpg.connect(os.environ[\"DATABASE_URL\"])
  await conn.execute(open(\"/tmp/m.sql\").read())
  print(\"applied\")
  await conn.close()
asyncio.run(main())
"'
```

For destructive migrations: prefix with a `pg_dump` to a host folder. For
RLS / trigger migrations: dry-run first by replacing `COMMIT;` with
`ROLLBACK;` (the helper script in CONTRIBUTING.md does this automatically).

`POST /api/health/run-migrations` runs every `*.sql` in the migrations
directories that doesn't have `seed`/`test`/`bak` in its name. It is
admin-gated since this branch.

---

## Rollback

Coolify keeps previous Docker images. Quickest rollback:

```bash
# 1. Identify the previous good image tag
ssh asystem-proxmox 'docker images | grep g5ktpm7dy1abguwpy4tm7dpv | head -5'

# 2. Stop current container, run previous image
ssh asystem-proxmox 'docker stop g5ktpm7dy1abguwpy4tm7dpv-... && \
                     docker run -d --name <name> <prev-image-id> ...'
```

For a clean rollback via Coolify: redeploy from a previous git commit by
temporarily setting `git_commit_sha` in the application config, then
calling `/deploy`.

For DB schema rollback: every migration should ship with a paired
`<n>_revert.sql` (we don't always have these — write one for any
migration that adds a constraint or trigger).

---

## Common breakages

| Symptom | Cause | Fix |
|---|---|---|
| `ssh: Operation timed out` to ax41 | Hetzner network blip or host overload | wait 60–120s, check Hetzner Cloud Console; if persistent, reboot from console |
| Coolify API returns `error code: 522` | Coolify backend overloaded (usually during a heavy build) | wait 30s and retry; check `c.asystem.kg` itself |
| Deploy build fails on `npm install` | New dep conflict with Tailwind 4 | use `--legacy-peer-deps` in Dockerfile RUN, or pin offending dep |
| Container in `running:unhealthy` | Healthcheck path requires auth or returned 500 | check the healthcheck command in Coolify; ensure it hits `/api/health` (no auth) |
| All `*.asystem.kg` 522 / dead | ax41 down. SSH itself won't connect. | reboot from Hetzner Console; check disk space; check RAM exhaustion |
| Login starts returning 401 unexpectedly | `JWT_SECRET_KEY` env regenerated mid-flight (auto-fallback in `backend/config.py`) | set `JWT_SECRET_KEY` explicitly in Coolify env, redeploy |
| Frontend shows "Failed to fetch" | wrong `NEXT_PUBLIC_API_URL` or browser CORS block | verify env in Coolify FE app, hit `/api/v1/billing/plans` from terminal |

---

## Backups

The repo ships [`scripts/backup_pg.sh`](scripts/backup_pg.sh) — `pg_dump`
piped through gzip, with mtime-based retention. Drop it in
`/opt/orgon/scripts/` on the proxmox host and add a cron entry as
described in [`CI-CD.md`](CI-CD.md#backups).

Default behaviour: `/var/backups/orgon/orgon-<utc-timestamp>.sql.gz`,
retain 14 days, refuse to keep dumps under 4 KiB (so a partial run can't
silently age out the good copies).

To take a manual one-off backup right now:

```bash
ssh asystem-proxmox 'docker exec coolify-postgres-... pg_dump -U orgon -F c orgon \
  > /tmp/orgon-$(date +%Y%m%d).pgdump'
scp asystem-proxmox:/tmp/orgon-*.pgdump ./backups/
```
