"""Monitoring endpoints — health, metrics, Prometheus."""

import os
import time
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
import httpx

from backend.rbac import require_roles

logger = logging.getLogger("orgon.monitoring")

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

_AUTH_ADMIN = require_roles("platform_admin", "company_admin")

START_TIME = time.time()


async def check_service(url: str, timeout: float = 5.0) -> dict:
    """Check external service health."""
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            r = await client.get(url)
            return {"status": "ok" if r.status_code < 400 else "degraded", "status_code": r.status_code}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)[:120]}


async def get_count(pool, table: str, where: str = None) -> int:
    """Get row count from a table."""
    try:
        q = f"SELECT COUNT(*) as cnt FROM {table}"
        if where:
            q += f" WHERE {where}"
        async with pool.acquire() as conn:
            row = await conn.fetchrow(q)
            return row["cnt"] if row else 0
    except Exception as e:
        logger.warning(f"Count query failed for {table}: {e}")
        return -1


@router.get("/health")
async def detailed_health(request: Request, user: dict = Depends(_AUTH_ADMIN)):
    """Extended health check with service statuses and metrics. Admin-only."""
    from backend.websocket_manager import ws_manager

    pool = request.app.state.db_pool

    # Check services in parallel
    import asyncio
    docling_task = check_service("https://docling.asystem.ai/health")
    onlyoffice_task = check_service("https://office.asystem.ai/healthcheck")
    docling_status, onlyoffice_status = await asyncio.gather(docling_task, onlyoffice_task)

    # DB check
    db_status = "ok"
    try:
        async with pool.acquire() as conn:
            await conn.fetchrow("SELECT 1")
    except Exception as e:
        db_status = f"error: {e}"

    # Metrics
    total_users = await get_count(pool, "users")
    total_orgs = await get_count(pool, "organizations")
    total_wallets = await get_count(pool, "wallets")
    total_transactions = await get_count(pool, "transactions")
    pending_transactions = await get_count(pool, "transactions", "status=pending")

    # WS connections
    ws_connections = sum(len(v) for v in ws_manager.active_connections.values()) if hasattr(ws_manager, "active_connections") else 0

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "services": {
            "database": db_status,
            "redis": "not_configured",
            "websocket": {"active_connections": ws_connections},
            "docling": docling_status,
            "onlyoffice": onlyoffice_status,
        },
        "metrics": {
            "total_users": total_users,
            "total_orgs": total_orgs,
            "total_wallets": total_wallets,
            "total_transactions": total_transactions,
            "pending_transactions": pending_transactions,
        },
    }


@router.get("/metrics")
async def prometheus_metrics(request: Request, user: dict = Depends(_AUTH_ADMIN)):
    """Prometheus-compatible metrics endpoint. Admin-only — leaks counts."""
    from fastapi.responses import PlainTextResponse
    from backend.websocket_manager import ws_manager

    pool = request.app.state.db_pool

    total_users = await get_count(pool, "users")
    total_orgs = await get_count(pool, "organizations")
    total_wallets = await get_count(pool, "wallets")
    total_transactions = await get_count(pool, "transactions")
    pending_transactions = await get_count(pool, "transactions", "status=pending")
    ws_connections = sum(len(v) for v in ws_manager.active_connections.values()) if hasattr(ws_manager, "active_connections") else 0

    uptime = round(time.time() - START_TIME, 1)

    lines = [
        "# HELP orgon_uptime_seconds Time since backend started",
        "# TYPE orgon_uptime_seconds gauge",
        f"orgon_uptime_seconds {uptime}",
        "",
        "# HELP orgon_users_total Total registered users",
        "# TYPE orgon_users_total gauge",
        f"orgon_users_total {total_users}",
        "",
        "# HELP orgon_organizations_total Total organizations",
        "# TYPE orgon_organizations_total gauge",
        f"orgon_organizations_total {total_orgs}",
        "",
        "# HELP orgon_wallets_total Total wallets",
        "# TYPE orgon_wallets_total gauge",
        f"orgon_wallets_total {total_wallets}",
        "",
        "# HELP orgon_transactions_total Total transactions",
        "# TYPE orgon_transactions_total gauge",
        f"orgon_transactions_total {total_transactions}",
        "",
        "# HELP orgon_transactions_pending Pending transactions",
        "# TYPE orgon_transactions_pending gauge",
        f"orgon_transactions_pending {pending_transactions}",
        "",
        "# HELP orgon_websocket_connections Active WebSocket connections",
        "# TYPE orgon_websocket_connections gauge",
        f"orgon_websocket_connections {ws_connections}",
        "",
    ]

    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4")
