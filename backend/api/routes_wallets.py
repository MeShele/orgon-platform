"""Wallet CRUD endpoints."""

import logging
from decimal import Decimal

import httpx
from fastapi import APIRouter, HTTPException, Request

from backend.safina.models import CreateWalletRequest
from fastapi import Depends
from backend.rbac import require_roles
from backend.dependencies import get_user_org_ids, get_db_pool
from backend.safina.errors import SafinaError

logger = logging.getLogger("orgon.api.wallets")

router = APIRouter(prefix="/api/wallets", tags=["wallets"])

# On-chain balance fallback. Safina's ledger monitor is known to leave
# `/wallet_tokens` at value:0 even when the chain holds funds (documented,
# unresolved on their side — see docs/SAFINA_DEPOSIT_BALANCE_ISSUE_RU.md and
# wallet_service._create_wallet_internal's min_signs note). When Safina
# returns nothing we read the real balance straight from the chain so the
# wallet detail page shows the truth instead of a false 0. Read-only,
# best-effort — mirrors the asystem-core sema fix (orgon-wallet-balance edge).
_ORGON_ONCHAIN_BASE = {
    5810: "https://quasargate.orgon.space",  # ORGON Quasar testnet gate (TronGrid-style)
}
_ORGON_SUN = Decimal(1_000_000)  # ORGON inherits Tron's 6-decimal "sun" base unit
# orc20 test contracts → (symbol, decimals). Extend as ORGON ships tokens.
_ORC20_SYMBOLS = {
    "oZo9ZekPmHpj6KBbEHSA9686JKNuXY4N5z": ("USDT", 6),
}


async def _onchain_tokens(network: int, addr: str) -> list[dict]:
    """Live on-chain token list for an ORGON-network wallet, shaped like
    Safina's `/wallet_tokens` rows ({token, network, value, decimals}) so
    the frontend renders it unchanged. `value` is human-decimal (sun ÷ 1e6),
    matching Safina. Node unreachable → return [] (caller keeps the empty
    Safina result — never raises)."""
    base = _ORGON_ONCHAIN_BASE.get(network)
    if not base or not addr:
        return []
    out: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{base}/v1/accounts/{addr}",
                headers={"User-Agent": "orgon-platform/1"},
            )
            r.raise_for_status()
            data = (r.json() or {}).get("data") or {}
        native = Decimal(str(data.get("balance") or 0)) / _ORGON_SUN
        if native > 0:
            out.append({
                "token": "ORGON", "network": network,
                "value": format(native, "f"), "decimals": 6,
                "source": "onchain",
            })
        for t in data.get("orc20") or []:
            sym, dec = _ORC20_SYMBOLS.get(
                t.get("key"), ("TOKEN", int(t.get("decimals") or 6)),
            )
            raw = Decimal(str(t.get("value") or 0))
            if raw <= 0:
                continue
            out.append({
                "token": sym, "network": network,
                "value": format(raw / (Decimal(10) ** dec), "f"),
                "decimals": dec, "source": "onchain",
            })
    except Exception as e:
        logger.warning("ORGON on-chain balance fallback failed for %s: %s", addr, e)
        return []
    return out


def _all_zero(tokens: list) -> bool:
    """True when Safina reports nothing spendable — either an empty list or
    only zero-value rows. Safina's monitor returns a `value:0` row (not an
    empty list) for wallets it never registered, so an emptiness check alone
    misses the common case."""
    if not tokens:
        return True
    for t in tokens:
        try:
            if Decimal(str((t or {}).get("value") or 0)) > 0:
                return False
        except Exception:
            # Non-numeric value → assume real, don't override it.
            return False
    return True


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
async def get_wallet_tokens(
    name: str,
    http_request: Request,
    user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor", "end_user", "platform_admin")),
):
    """Tenant-aware token list for a wallet.

    The singleton service signs Safina calls with the global env EC,
    which Safina rejects (or returns empty for) for tenant-owned
    wallets. Resolve the wallet's tenant from local DB and call
    /ece/wallet_tokens/{name} under that tenant's EC so the balances
    actually come back populated.
    """
    base = _get_service()
    local = await base._db.fetchrow(
        "SELECT organization_id, addr, network FROM wallets WHERE name = $1 OR my_unid = $1",
        params=(name,),
    )
    org_id = local.get("organization_id") if local else None
    addr = local.get("addr") if local else None
    network = local.get("network") if local else None
    try:
        tokens: list = []
        if org_id:
            from backend.safina.factory import get_safina_client_for_org
            pool = get_db_pool(http_request)
            tc = await get_safina_client_for_org(pool, str(org_id))
            try:
                raw = await tc._request("GET", f"wallet_tokens/{name}")
                # Endpoint returns a list of token dicts already in the
                # shape the frontend expects.
                tokens = raw if isinstance(raw, list) else []
            finally:
                await tc.close()
        else:
            # No tenant attached → singleton (e.g. platform_admin).
            tokens = await base.get_wallet_tokens(name)

        # Safina's ledger monitor is known to report value:0 even when the
        # chain holds funds (empty list OR a lone zero-value row). When
        # nothing spendable comes back, substitute the real on-chain balance
        # so the wallet page shows the truth instead of a false 0. Only for
        # ORGON nets; keep the Safina rows if the node is unreachable.
        if addr and _all_zero(tokens):
            try:
                net_int = int(network)
            except (TypeError, ValueError):
                net_int = None
            if net_int is not None:
                onchain = await _onchain_tokens(net_int, addr)
                if onchain:
                    tokens = onchain
        return tokens
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
