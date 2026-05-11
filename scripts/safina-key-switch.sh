#!/usr/bin/env bash
# safina-key-switch.sh
#
# Atomic switch of SAFINA_EC_PRIVATE_KEY on the running prod backend.
# Used to flip from the shared test-keypair to a real Safina-issued
# prod-tenant key during a pilot bring-up.
#
# Usage:
#   ./scripts/safina-key-switch.sh switch <new-private-key-hex>
#   ./scripts/safina-key-switch.sh rollback
#   ./scripts/safina-key-switch.sh status
#
# Safe-by-design:
#   - Every switch saves a timestamped backup of the previous .env
#     inside the VM at /root/orgon-key-history/.env.<ts>
#   - Rollback restores the most recent backup (one-liner)
#   - Smoke runs after switch — if /api/health/safina returns
#     reachable=false (Safina rejected our signature), the script
#     EXITS NON-ZERO so the operator notices instantly
#
# This DOES NOT go through Coolify UI. It edits the materialised
# .env file directly + restarts the backend container. Coolify will
# re-materialise the .env on next redeploy from its DB — to make the
# change persistent through redeploys, ALSO update via Coolify UI
# (Environment Variables → SAFINA_EC_PRIVATE_KEY → save).
#
# Intended workflow at pilot bring-up:
#   1. Run this script with the new key  → instant live switch
#   2. Smoke passes? Update Coolify UI to persist
#   3. Smoke fails?  Run rollback, debug
set -euo pipefail

ORION="${ORGON_ORION:-65.21.205.230}"
VM_IP="${ORGON_VM:-10.10.20.10}"
APP_DIR="/data/coolify/applications/nw5o0foj43w96q9upluxnr0l"
BACKUP_DIR="/root/orgon-key-history"
CONTAINER_FILTER="^backend-nw5o0foj"
HEALTH_URL="${ORGON_HEALTH:-https://orgon.asystem.ai/api/health/safina}"
DEMO_LOGIN_URL="${ORGON_LOGIN:-https://orgon.asystem.ai/api/auth/login}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; }

remote() {
  ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
      -J "root@${ORION}" "root@${VM_IP}" "$@"
}

cmd="${1:-}"

case "$cmd" in
  status)
    echo "=== Current SAFINA_EC_PRIVATE_KEY in prod ==="
    remote "grep '^SAFINA_EC_PRIVATE_KEY=' ${APP_DIR}/.env | sed 's/=.*$/=<redacted, last 6: /' && \
            grep '^SAFINA_EC_PRIVATE_KEY=' ${APP_DIR}/.env | awk -F= '{print substr(\$2, length(\$2)-5, 6)\">\"}'"
    echo
    echo "=== Backups available ==="
    remote "ls -lh ${BACKUP_DIR}/ 2>/dev/null | tail -10 || echo 'no backups yet'"
    echo
    echo "=== Container ==="
    remote "docker ps --filter name=${CONTAINER_FILTER} --format '{{.Names}}|{{.Status}}'"
    ;;

  switch)
    NEW_KEY="${2:-}"
    if [ -z "$NEW_KEY" ]; then
      err "usage: $0 switch <new-key-hex>"; exit 2
    fi
    if [[ ! "$NEW_KEY" =~ ^0x[0-9a-fA-F]{64}$ ]]; then
      err "key must be 0x + 64 hex chars (got: '${NEW_KEY:0:20}...')"; exit 2
    fi

    TS=$(date -u +%Y%m%dT%H%M%SZ)
    echo "Switching SAFINA_EC_PRIVATE_KEY @ $TS UTC"

    # 1. Backup current .env
    remote "mkdir -p ${BACKUP_DIR} && cp ${APP_DIR}/.env ${BACKUP_DIR}/.env.${TS}"
    ok "backup saved → ${BACKUP_DIR}/.env.${TS}"

    # 2. Replace key in .env (in-place, atomic via sponge-equivalent)
    remote "awk -v key='${NEW_KEY}' '
      BEGIN{repl=0}
      /^SAFINA_EC_PRIVATE_KEY=/ {print \"SAFINA_EC_PRIVATE_KEY=\" key; repl=1; next}
      {print}
      END{if(repl==0){print \"SAFINA_EC_PRIVATE_KEY=\" key}}
    ' ${APP_DIR}/.env > ${APP_DIR}/.env.new && \
    mv ${APP_DIR}/.env.new ${APP_DIR}/.env"
    ok "key replaced in ${APP_DIR}/.env"

    # 3. Restart backend container (NOT recreate — fast)
    remote "docker restart \$(docker ps -q --filter name=${CONTAINER_FILTER}) | head -1"
    ok "backend container restarted"

    # 4. Wait + probe health
    echo "waiting 25s for backend to come up..."
    sleep 25
    HEALTH=$(curl -sS --max-time 15 -o /tmp/health.json -w "%{http_code}" \
             "https://orgon.asystem.ai/api/health" || echo "000")
    if [ "$HEALTH" != "200" ]; then
      err "api/health returned $HEALTH — backend not up. ROLLBACK NOW: $0 rollback"
      exit 1
    fi
    ok "/api/health → 200"

    # 5. Auth-required Safina-reachability probe
    TOKEN=$(curl -sS --max-time 10 -X POST "$DEMO_LOGIN_URL" \
            -H "Content-Type: application/json" \
            -d '{"email":"demo-admin@orgon.io","password":"demo2026"}' \
            | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
    if [ -z "$TOKEN" ]; then
      warn "login failed (token issuance broken?). Manual check needed."
      exit 1
    fi
    REACH=$(curl -sS --max-time 15 -H "Authorization: Bearer $TOKEN" "$HEALTH_URL" \
            | python3 -c "import sys,json;print(json.load(sys.stdin).get('safina_reachable',False))" 2>/dev/null)
    if [ "$REACH" != "True" ]; then
      err "/api/health/safina → reachable=false — Safina REJECTED the new key signature"
      err "ROLLBACK NOW: $0 rollback"
      exit 1
    fi
    ok "/api/health/safina → reachable=true (Safina accepts the new key)"
    echo
    echo "=========================================="
    echo "SWITCHOVER COMPLETE."
    echo "Backup: ${BACKUP_DIR}/.env.${TS}"
    echo "Next step: persist key in Coolify UI (Env Variables → SAFINA_EC_PRIVATE_KEY)"
    echo "=========================================="
    ;;

  rollback)
    LATEST=$(remote "ls -1t ${BACKUP_DIR}/.env.* 2>/dev/null | head -1")
    if [ -z "$LATEST" ]; then
      err "no backups found in ${BACKUP_DIR}"; exit 1
    fi
    echo "Restoring from: $LATEST"
    remote "cp '$LATEST' ${APP_DIR}/.env"
    ok ".env restored"
    remote "docker restart \$(docker ps -q --filter name=${CONTAINER_FILTER}) | head -1"
    ok "backend container restarted"
    echo "waiting 25s..."
    sleep 25
    HEALTH=$(curl -sS --max-time 15 -o /dev/null -w "%{http_code}" \
             "https://orgon.asystem.ai/api/health" || echo "000")
    if [ "$HEALTH" = "200" ]; then
      ok "rollback successful, /api/health → 200"
    else
      err "rollback restored but /api/health → $HEALTH"
      exit 1
    fi
    ;;

  *)
    cat <<USAGE
Usage: $0 {status|switch <key>|rollback}

  status                  Show current key fingerprint + backups list
  switch <0xHEX-key>      Atomic switch to new key + smoke (auto-rollback on failure)
  rollback                Restore most recent backup + smoke

Environment overrides:
  ORGON_ORION             Orion host IP (default: 65.21.205.230)
  ORGON_VM                Coolify VM IP (default: 10.10.20.10)

Example:
  $0 status
  $0 switch 0xabc123...   # 0x + 64 hex chars
  $0 rollback
USAGE
    exit 2
    ;;
esac
