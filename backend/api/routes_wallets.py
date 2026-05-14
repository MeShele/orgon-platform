"""Wallet CRUD endpoints."""

from fastapi import APIRouter, HTTPException, Request

from backend.safina.models import CreateWalletRequest
from fastapi import Depends
from backend.rbac import require_roles
from backend.dependencies import get_user_org_ids, get_db_pool
from backend.safina.errors import SafinaError

router = APIRouter(prefix="/api/wallets", tags=["wallets"])


def _get_service():
    from backend.main import get_wallet_service
    return get_wallet_service()


@router.get("")
async def list_wallets(
    user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor", "end_user", "platform_admin")),
    org_ids: list = Depends(get_user_org_ids)
):
    """List wallets filtered by user organizations."""
    service = _get_service()
    return await service.list_wallets(org_ids=org_ids)



@router.get("/by-unid/{unid}")
async def get_wallet_by_unid(unid: str, user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor", "end_user", "platform_admin"))):
    """Get wallet by UNID (Safina wallet identifier)."""
    service = _get_service()
    try:
        wallet = await service.get_wallet_by_unid(unid)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        return wallet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching wallet by UNID: {e}")


@router.get("/{name}")
async def get_wallet(
    name: str,
    http_request: Request,
    user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor", "end_user", "platform_admin")),
):
    """Get wallet details, enriched with Safina-side fields.

    The singleton wallet service signs Safina calls with the global
    env key, which is invisible to tenant-owned wallets — Safina
    returns `{}` and the response falls back to the local DB row,
    which has no `slist`/`unid`. We resolve the wallet's tenant from
    the local row and call Safina under that tenant's EC, so the
    response carries the live `slist`, `unid`, `addrs`, `wallet_type`
    fields useful for debugging the wallet's signer setup.
    """
    service = _get_service()
    try:
        wallet = await service.get_wallet(name)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        # Enrich with tenant-scoped Safina detail if we know the org.
        org_id = wallet.get("organization_id")
        if org_id:
            from backend.safina.factory import get_safina_client_for_org
            try:
                pool = get_db_pool(http_request)
                tc = await get_safina_client_for_org(pool, str(org_id))
                try:
                    target = wallet.get("name") or name
                    detail = await tc._request("GET", f"wallet/{target}")
                    for k in ("slist", "unid", "addrs", "wallet_type", "myFlags"):
                        if detail.get(k) is not None:
                            wallet[k] = detail[k]
                    wallet["safina_signer"] = tc._signer.address
                finally:
                    await tc.close()
            except Exception as e:
                # Enrichment is best-effort; the local fields still ship.
                wallet["safina_detail_error"] = str(e)
        return wallet
    except HTTPException:
        raise
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching wallet: {e}")


@router.get("/{name}/tokens")
async def get_wallet_tokens(name: str, user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor", "end_user", "platform_admin"))):
    """Get tokens for a wallet."""
    service = _get_service()
    try:
        return await service.get_wallet_tokens(name)
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tokens: {e}")


@router.post("", status_code=201)
async def create_wallet(
    request: CreateWalletRequest,
    http_request: Request,
    user: dict = Depends(require_roles("company_admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    """Create a new wallet using the caller's tenant-scoped Safina EC key.

    Mutations must NOT use the global signer — that would collapse
    every ORGON tenant into the same Safina customer. We build a
    per-request SafinaPayClient signed with the EC key stored on the
    caller's organization (column safina_ec_private_key), then ask
    that client to create the wallet.

    The new wallet row is also attached to the caller's organization
    so list-filtering shows it under their tenant.
    """
    from backend.safina.factory import get_safina_client_for_org

    org_id = org_ids[0] if org_ids else None
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="User is not attached to any organization — cannot create wallet",
        )

    pool = get_db_pool(http_request)
    tenant_client = await get_safina_client_for_org(pool, org_id)
    try:
        # Bypass the singleton service: drive the tenant-signed client directly.
        from backend.services.wallet_service import WalletService
        tenant_service = WalletService(tenant_client, _get_service()._db)
        unid = await tenant_service.create_wallet(
            request=request, organization_id=str(org_id),
        )
        # Activation is async on Safina's side (5–10 min). We return
        # status=pending so the UI can render a "creating…" notice and
        # not redirect into a half-baked wallet detail. The scheduler
        # sync writes the row to DB only after Safina publishes an addr.
        return {
            "myUNID": unid,
            "status": "pending",
            "message": (
                "Кошелёк создан в Сафине. Активация занимает 5–10 минут — "
                "появится в списке автоматически после получения адреса."
            ),
        }
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await tenant_client.close()


@router.patch("/{name}/label")
async def update_label(name: str, label: str, user: dict = Depends(require_roles("company_admin"))):
    """Update wallet local label."""
    service = _get_service()
    if not await service.update_label(name, label):
        raise HTTPException(status_code=404, detail="Wallet not found")
    return {"ok": True}


@router.post("/{name}/favorite")
async def toggle_favorite(name: str, user: dict = Depends(require_roles("company_admin", "company_operator"))):
    """Toggle wallet favorite status."""
    service = _get_service()
    if not await service.toggle_favorite(name):
        raise HTTPException(status_code=404, detail="Wallet not found")
    return {"ok": True}


@router.post("/sync")
async def sync_wallets(user: dict = Depends(require_roles("company_admin"))):
    """Force sync wallets from Safina API."""
    service = _get_service()
    try:
        await service.sync_wallets()
        return {"ok": True}
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
