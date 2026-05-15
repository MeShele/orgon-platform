"""Public /v1/* API — merchant-facing endpoints.

All routes here are guarded by `MerchantHMACAuthMiddleware`. On
authenticated requests, the middleware writes:

    request.state.merchant_id          : str (uuid)
    request.state.merchant_api_key_id  : str
    request.state.merchant_scopes      : list[str]

Subsequent endpoints scope DB queries by `merchant_id` — never trust
client-supplied tenant ids.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/v1", tags=["public-v1"])


@router.get("/health")
async def public_health() -> dict:
    """Liveness probe. Unauthenticated by middleware exempt list."""
    return {"status": "ok", "service": "orgon-public-v1"}


@router.get("/ping")
async def public_ping(request: Request) -> dict:
    """Authenticated ping. Echoes back caller identity so an integrator
    can verify HMAC signing end-to-end before wiring real flows."""
    return {
        "ok": True,
        "merchant_id": getattr(request.state, "merchant_id", None),
        "scopes": getattr(request.state, "merchant_scopes", []),
        "api_key_id": getattr(request.state, "merchant_api_key_id", None),
    }
