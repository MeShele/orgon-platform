"""Health check endpoints."""

from fastapi import APIRouter, Request
from datetime import datetime, timezone
import logging

logger = logging.getLogger("orgon.api.health")

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health():
    """Basic health check."""
    from backend.database.db import get_db
    db = get_db()
    last_sync = db.fetchone("SELECT value FROM sync_state WHERE key = 'balances_synced'")
    return {
        "status": "ok",
        "service": "orgon",
        "last_sync": last_sync["value"] if last_sync else None,
    }


@router.get("/safina")
async def safina_health():
    """Check Safina API availability."""
    from backend.main import get_safina_client
    client = get_safina_client()
    try:
        healthy = await client.check_health()
        return {"status": "ok" if healthy else "degraded", "safina_reachable": healthy}
    except Exception as e:
        return {"status": "error", "safina_reachable": False, "error": str(e)}


@router.get("/detailed")
async def detailed_health():
    """
    Detailed health check with all service statuses.

    Returns comprehensive health information including:
    - Database status
    - Safina API connectivity
    - Telegram integration status
    - ASAGENT bridge status
    - Cache health
    - Service versions
    """
    from backend.main import (
        get_safina_client,
        get_network_service,
        get_asagent_bridge,
        _telegram_notifier,
    )
    from backend.database.db import get_db

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "services": {},
    }

    # Database health
    try:
        db = get_db()
        try:
            last_sync = db.fetchone("SELECT value FROM sync_state WHERE key = 'balances_synced'")
            last_sync_val = last_sync["value"] if last_sync else None
        except Exception:
            last_sync_val = "postgresql_mode"
        health_status["services"]["database"] = {
            "status": "healthy",
            "last_sync": last_sync_val,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    # Safina API health
    try:
        client = get_safina_client()
        if client:
            safina_healthy = await client.check_health()
            health_status["services"]["safina_api"] = {
                "status": "healthy" if safina_healthy else "degraded",
                "reachable": safina_healthy,
            }
            if not safina_healthy:
                health_status["status"] = "degraded"
        else:
            health_status["services"]["safina_api"] = {
                "status": "not_configured",
            }
    except Exception as e:
        logger.error(f"Safina health check failed: {e}")
        health_status["services"]["safina_api"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    # Cache health
    try:
        network_service = get_network_service()
        if network_service:
            cache_stats = network_service.get_cache_stats()
            import inspect
            if inspect.isawaitable(cache_stats):
                cache_stats = await cache_stats
            if not isinstance(cache_stats, dict):
                cache_stats = {"raw": str(cache_stats)}
            health_status["services"]["cache"] = {
                "status": "healthy",
                "stats": cache_stats,
            }
        else:
            health_status["services"]["cache"] = {"status": "not_initialized"}
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        health_status["services"]["cache"] = {
            "status": "error",
            "error": str(e),
        }

    # Telegram integration health
    if _telegram_notifier:
        try:
            telegram_ok = await _telegram_notifier.test_connection()
            health_status["services"]["telegram"] = {
                "status": "healthy" if telegram_ok else "degraded",
                "configured": True,
                "connected": telegram_ok,
            }
        except Exception as e:
            logger.error(f"Telegram health check failed: {e}")
            health_status["services"]["telegram"] = {
                "status": "error",
                "configured": True,
                "connected": False,
                "error": str(e),
            }
    else:
        health_status["services"]["telegram"] = {
            "status": "not_configured",
            "configured": False,
        }

    # ASAGENT Bridge health
    bridge = get_asagent_bridge()
    if bridge:
        try:
            bridge_reachable = await bridge.ping()
            health_status["services"]["asagent_bridge"] = {
                "status": "healthy" if bridge_reachable else "degraded",
                "configured": True,
                "gateway_reachable": bridge_reachable,
                "skills_registered": bridge.is_ready,
            }
        except Exception as e:
            logger.error(f"ASAGENT health check failed: {e}")
            health_status["services"]["asagent_bridge"] = {
                "status": "error",
                "configured": True,
                "error": str(e),
            }
    else:
        health_status["services"]["asagent_bridge"] = {
            "status": "not_configured",
            "configured": False,
        }

    return health_status


@router.get("/services")
async def check_services():
    """Check which services are initialized."""
    from backend.main import (
        _async_db, _safina_client, _wallet_service, _transaction_service,
        _dashboard_service, _network_service, _signature_service,
        _organization_service, _auth_service, _sync_service,
        _balance_service, _scheduled_transaction_service,
        _address_book_service, _analytics_service, _audit_service,
        _user_service, _partner_service, _webhook_service,
    )
    return {
        "async_db": _async_db is not None,
        "async_db_pool": (_async_db._pool is not None) if _async_db else False,
        "safina_client": _safina_client is not None,
        "wallet_service": _wallet_service is not None,
        "transaction_service": _transaction_service is not None,
        "dashboard_service": _dashboard_service is not None,
        "network_service": _network_service is not None,
        "signature_service": _signature_service is not None,
        "organization_service": _organization_service is not None,
        "auth_service": _auth_service is not None,
        "sync_service": _sync_service is not None,
        "balance_service": _balance_service is not None,
        "scheduled_tx_service": _scheduled_transaction_service is not None,
        "address_book_service": _address_book_service is not None,
        "analytics_service": _analytics_service is not None,
        "audit_service": _audit_service is not None,
        "user_service": _user_service is not None,
        "partner_service": _partner_service is not None,
        "webhook_service": _webhook_service is not None,
    }


@router.post("/run-migrations")
async def run_migrations(request: Request):
    """Run PostgreSQL migrations manually."""
    from pathlib import Path

    pool = getattr(request.app.state, 'db_pool', None)
    if not pool:
        return {"status": "error", "message": "No PostgreSQL pool in app.state"}

    # Two migration directories exist in the codebase
    base = Path(__file__).parent.parent
    dirs = [base / "migrations", base / "database" / "migrations"]

    results = []
    migration_files = []
    for d in dirs:
        if d.exists():
            for f in sorted(d.glob("*.sql")):
                skip = ('.bak' in f.name or 'test' in f.name or 'seed' in f.name
                        or f.name == 'README.md' or f.name.startswith('._'))
                if f.suffix == '.sql' and not skip:
                    migration_files.append(f)

    for mf in migration_files:
        try:
            sql = mf.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                sql = mf.read_text(encoding='latin-1')
            except Exception:
                results.append({"file": mf.name, "status": "error", "error": "encoding error"})
                continue
        try:
            async with pool.acquire() as conn:
                await conn.execute(sql)
            results.append({"file": mf.name, "status": "ok"})
        except Exception as e:
            err = str(e)
            if "already exists" in err.lower() or "duplicate" in err.lower():
                results.append({"file": mf.name, "status": "already_applied"})
            else:
                results.append({"file": mf.name, "status": "error", "error": err[:300]})

    ok = sum(1 for r in results if r["status"] == "ok")
    skip = sum(1 for r in results if r["status"] == "already_applied")
    fail = sum(1 for r in results if r["status"] == "error")
    return {"status": "done", "applied": ok, "skipped": skip, "errors": fail, "details": results}
