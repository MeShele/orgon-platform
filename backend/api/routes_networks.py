"""Network and token info endpoints."""

from fastapi import APIRouter, HTTPException, Depends

from backend.rbac import require_roles

_AUTH_ADMIN = require_roles("platform_admin", "company_admin")

from backend.safina.errors import SafinaError

router = APIRouter(prefix="/api", tags=["networks"])


def _get_network_service():
    """Get NetworkService instance."""
    from backend.main import get_network_service
    return get_network_service()


def _get_balance_service():
    """Get BalanceService instance."""
    from backend.main import get_balance_service
    return get_balance_service()


@router.get("/networks")
async def list_networks(status: int = 1):
    """
    Get network directory with caching.

    Args:
        status: 1 for active networks (default), 0 for disabled

    Returns:
        List of networks
    """
    service = _get_network_service()
    try:
        networks = await service.get_networks(status=status)
        return [n.model_dump() for n in networks]
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch networks: {e}")


@router.get("/networks/{network_id}")
async def get_network(network_id: int):
    """
    Get specific network by ID.

    Args:
        network_id: Network ID to lookup

    Returns:
        Network details or 404
    """
    service = _get_network_service()
    try:
        network = await service.get_network_by_id(network_id)
        if not network:
            raise HTTPException(status_code=404, detail="Network not found")
        return network.model_dump()
    except HTTPException:
        raise
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch network: {e}")


@router.get("/tokens")
async def list_tokens():
    """Get all user tokens with balances."""
    service = _get_balance_service()
    try:
        return await service.get_all_balances()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tokens: {e}")


@router.get("/tokens/summary")
async def token_summary():
    """Get aggregated token balances."""
    service = _get_balance_service()
    try:
        return await service.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {e}")


@router.get("/tokens/info")
async def tokens_info():
    """
    Get token commission info directory with caching.

    Returns:
        List of token commission info
    """
    service = _get_network_service()
    try:
        tokens_info = await service.get_tokens_info()
        return [t.model_dump() for t in tokens_info]
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tokens info: {e}")


@router.get("/tokens/info/{token}")
async def token_info(token: str):
    """
    Get commission info for a specific token.

    Args:
        token: Token identifier (format: "network:::TOKEN")

    Returns:
        Token commission info or 404
    """
    service = _get_network_service()
    try:
        info = await service.get_token_info(token)
        if not info:
            raise HTTPException(status_code=404, detail="Token info not found")
        return info.model_dump()
    except HTTPException:
        raise
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch token info: {e}")


@router.get("/cache/stats")
async def cache_stats():
    """
    Get cache statistics for monitoring.

    Returns:
        Cache age and sizes for networks and tokens_info
    """
    service = _get_network_service()
    try:
        stats = service.get_cache_stats()
        import inspect
        if inspect.isawaitable(stats):
            stats = await stats
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {e}")


@router.post("/cache/refresh")
async def refresh_cache(user: dict = Depends(_AUTH_ADMIN)):
    """
    Force refresh of all network caches.

    Triggers background refresh of networks and tokens_info.
    """
    service = _get_network_service()
    try:
        await service.refresh_cache()
        return {"ok": True, "message": "Cache refresh initiated"}
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache refresh failed: {e}")
