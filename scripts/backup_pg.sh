#!/usr/bin/env bash
# Nightly Postgres backup with retention + optional off-site mirror.
#
# Usage:
#   DATABASE_URL=postgresql://…  \
#   ORGON_BACKUP_DIR=/var/backups/orgon \
#   ORGON_BACKUP_RETENTION_DAYS=14 \
#   # off-site (any S3-compatible — AWS S3, Cloudflare R2, Wasabi, MinIO):
#   ORGON_BACKUP_S3_BUCKET=s3://orgon-backups \
#   AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=… \
#   # for non-AWS S3-compatibles:
#   AWS_ENDPOINT_URL_S3=https://<account>.r2.cloudflarestorage.com \
#     ./scripts/backup_pg.sh
#
# Designed to run from cron on the host that has access to the Postgres
# database, or as a oneshot systemd unit + timer. Creates
# `<dir>/orgon-<timestamp>.sql.gz`, optionally uploads to S3 (if configured),
# then deletes local files older than RETENTION_DAYS.
#
# Sample systemd timer (every day at 03:00 UTC):
#   /etc/systemd/system/orgon-backup.service:
#     [Service]
#     Type=oneshot
#     EnvironmentFile=/etc/orgon/backup.env
#     ExecStart=/opt/orgon/scripts/backup_pg.sh
#   /etc/systemd/system/orgon-backup.timer:
#     [Timer]
#     OnCalendar=*-*-* 03:00:00 UTC
#     Persistent=true
#     [Install]
#     WantedBy=timers.target
#
# Cloudflare R2 setup notes:
#   1. Create a bucket in the R2 dashboard. Note the account ID.
#   2. Generate an R2 API token with "Object Read & Write" on that bucket.
#   3. Set:
#        AWS_ACCESS_KEY_ID=<token's access key>
#        AWS_SECRET_ACCESS_KEY=<token's secret>
#        AWS_ENDPOINT_URL_S3=https://<account-id>.r2.cloudflarestorage.com
#        ORGON_BACKUP_S3_BUCKET=s3://<bucket-name>
#   4. R2 supports the same retention via S3 lifecycle rules — set them in
#      the dashboard, not here, so cross-region failover doesn't lose history.

set -euo pipefail

DATABASE_URL="${DATABASE_URL:?DATABASE_URL must be set}"
BACKUP_DIR="${ORGON_BACKUP_DIR:-/var/backups/orgon}"
RETENTION_DAYS="${ORGON_BACKUP_RETENTION_DAYS:-14}"
S3_BUCKET="${ORGON_BACKUP_S3_BUCKET:-}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/orgon-${TS}.sql.gz"

mkdir -p "$BACKUP_DIR"

# ── 1. Local pg_dump ────────────────────────────────────────────────

echo "→ pg_dump ${DATABASE_URL%%@*}@…  →  $OUT"
pg_dump \
  --format=plain \
  --no-owner \
  --no-privileges \
  --quote-all-identifiers \
  "$DATABASE_URL" \
  | gzip -9 > "$OUT"

# Verify we got something larger than a header and a footer (~1KB).
SIZE_BYTES=$(stat -c%s "$OUT" 2>/dev/null || stat -f%z "$OUT")
if [ "${SIZE_BYTES:-0}" -lt 4096 ]; then
  echo "✗ backup looks too small ($SIZE_BYTES bytes) — aborting and removing"
  rm -f "$OUT"
  exit 1
fi
echo "✓ local backup OK ($SIZE_BYTES bytes)"

# ── 2. Optional off-site upload ─────────────────────────────────────

if [ -n "$S3_BUCKET" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "✗ ORGON_BACKUP_S3_BUCKET is set but 'aws' CLI is not installed" >&2
    echo "  install: pip install awscli  OR  apt-get install awscli" >&2
    exit 1
  fi
  S3_KEY="${S3_BUCKET%/}/orgon-${TS}.sql.gz"
  echo "→ uploading $OUT  →  $S3_KEY"
  # AWS_ENDPOINT_URL_S3 (and AWS_ACCESS_KEY_ID / SECRET) are read by the
  # CLI from the environment automatically.
  aws s3 cp "$OUT" "$S3_KEY" \
    --only-show-errors \
    --no-progress
  # Verify the upload landed at the expected size.
  REMOTE_SIZE=$(aws s3api head-object --bucket "${S3_BUCKET#s3://}" \
    --key "orgon-${TS}.sql.gz" \
    --query ContentLength --output text 2>/dev/null || echo "0")
  if [ "$REMOTE_SIZE" != "$SIZE_BYTES" ]; then
    echo "✗ off-site verification failed: remote=$REMOTE_SIZE local=$SIZE_BYTES" >&2
    exit 1
  fi
  echo "✓ off-site OK ($REMOTE_SIZE bytes)"
else
  echo "→ ORGON_BACKUP_S3_BUCKET unset — local-only backup"
fi

# ── 3. Local retention ──────────────────────────────────────────────

echo "→ pruning local files older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name 'orgon-*.sql.gz' -type f -mtime "+$RETENTION_DAYS" \
  -print -delete

echo "→ remaining local backups:"
ls -1tr "$BACKUP_DIR"/orgon-*.sql.gz 2>/dev/null | tail -5
