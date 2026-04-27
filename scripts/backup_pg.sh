#!/usr/bin/env bash
# Nightly Postgres backup with retention.
#
# Usage:
#   DATABASE_URL=postgresql://… ORGON_BACKUP_DIR=/var/backups/orgon \
#     ORGON_BACKUP_RETENTION_DAYS=14 ./scripts/backup_pg.sh
#
# Designed to run from cron on the proxmox/asystem host that has access to
# the Coolify postgres container, or as a oneshot systemd unit. Creates
# `<dir>/orgon-<timestamp>.sql.gz`, then deletes anything older than
# RETENTION_DAYS.

set -euo pipefail

DATABASE_URL="${DATABASE_URL:?DATABASE_URL must be set}"
BACKUP_DIR="${ORGON_BACKUP_DIR:-/var/backups/orgon}"
RETENTION_DAYS="${ORGON_BACKUP_RETENTION_DAYS:-14}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/orgon-${TS}.sql.gz"

mkdir -p "$BACKUP_DIR"

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
echo "✓ backup OK ($SIZE_BYTES bytes)"

echo "→ pruning anything older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name 'orgon-*.sql.gz' -type f -mtime "+$RETENTION_DAYS" -print -delete

echo "→ remaining backups:"
ls -1tr "$BACKUP_DIR"/orgon-*.sql.gz | tail -5
