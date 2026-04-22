"""Health check endpoints."""

from fastapi import APIRouter
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


@router.post("/run-migrations")
async def run_migrations():
    """Run PostgreSQL migrations manually."""
    from pathlib import Path
    from backend.main import _async_db

    if not _async_db or not _async_db._pool:
        return {"status": "error", "message": "No PostgreSQL connection"}

    migrations_dir = Path(__file__).parent.parent / "database" / "migrations"
    if not migrations_dir.exists():
        return {"status": "error", "message": f"Migrations dir not found: {migrations_dir}"}

    results = []
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for mf in migration_files:
        sql = mf.read_text()
        # Split into individual statements, respecting $$ blocks
        try:
            async with _async_db._pool.acquire() as conn:
                await conn.execute(sql)
            results.append({"file": mf.name, "status": "ok"})
        except Exception as e:
            err = str(e)
            if "already exists" in err.lower() or "duplicate" in err.lower():
                results.append({"file": mf.name, "status": "already_applied"})
            else:
                results.append({"file": mf.name, "status": "error", "error": err[:300]})
