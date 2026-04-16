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
        # Try Safina API directly
        wallet = await service.get_wallet(unid)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        return wallet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching wallet by UNID: {e}")


@router.get("/{name}")
async def get_wallet(name: str, user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor", "end_user", "platform_admin"))):
    """Get wallet details."""
    service = _get_service()
    try:
        wallet = await service.get_wallet(name)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
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
async def create_wallet(request: CreateWalletRequest, user: dict = Depends(require_roles("company_admin"))):
    """Create a new wallet (standard or multi-sig)."""
    service = _get_service()
    try:
        unid = await service.create_wallet(request=request)
        return {"myUNID": unid}
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))


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
