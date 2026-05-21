"""Transaction endpoints."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Response, Request

from backend.safina.models import SendTransactionRequest, RejectTransactionRequest
from fastapi import Depends
from backend.rbac import require_roles, require_any_auth
from backend.dependencies import get_user_org_ids, get_db_pool
from backend.safina.errors import SafinaError
from backend.services.transaction_service import (
    TransactionBlockedError,
    TransactionValidationError,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _get_service():
    from backend.main import get_transaction_service
    return get_transaction_service()


@router.get("")
async def list_transactions(
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(require_any_auth()),
    org_ids: list = Depends(get_user_org_ids),
    wallet: Optional[str] = None,
    status: Optional[str] = None,
    network: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """
    List transactions with optional filtering.

    Query parameters:
    - limit: Maximum number of results (default: 50)
    - offset: Number of results to skip (default: 0)
    - wallet: Filter by wallet name
    - status: Filter by status (pending/signed/confirmed/rejected)
    - network: Filter by network ID
    - from_date: Filter by date (ISO format, inclusive)
    - to_date: Filter by date (ISO format, inclusive)
    """
    service = _get_service()

    # Build filters dict
    filters = {}
    if wallet:
        filters["wallet_name"] = wallet
    if status:
        filters["status"] = status
    if network:
        filters["network"] = network
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date

    return await service.list_transactions(
        limit=limit,
        offset=offset,
        filters=filters if filters else None,
        org_ids=org_ids
    )


@router.get("/pending")
async def pending_signatures(user: dict = Depends(require_roles("company_admin", "company_operator"))):
    """Get transactions awaiting user signature."""
    service = _get_service()
    try:
        return await service.get_pending_signatures()
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{unid}")
async def get_transaction(unid: str, user: dict = Depends(require_any_auth())):
    """Get transaction details."""
    service = _get_service()
    tx = await service.get_transaction(unid)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.get("/{unid}/signatures")
async def get_signatures(unid: str, user: dict = Depends(require_any_auth())):
    """Get all signatures for a transaction."""
    service = _get_service()
    try:
        return await service.get_tx_signatures(unid)
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/validate", status_code=200)
async def validate_transaction(request: SendTransactionRequest, user: dict = Depends(require_roles("company_admin", "company_operator", "end_user"))):
    """
    Validate transaction before sending (pre-flight check).

    Returns validation result with:
    - valid: bool
    - errors: list of error messages
    - warnings: list of warning messages
    - balance: current balance (if check_balance enabled)
    """
    service = _get_service()
    try:
        result = await service.validate_transaction(
            token=request.token,
            to_address=request.to_address,
            value=request.value,
            check_balance=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", status_code=201)
async def send_transaction(
    request: SendTransactionRequest,
    http_request: Request,
    validate: bool = True,
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    org_ids: list = Depends(get_user_org_ids),
):
    """Send a new transaction signed with the caller's tenant EC key.

    Must NOT route through the singleton service: that one is bound
    to the global SAFINA_EC_PRIVATE_KEY env var and would sign as the
    platform root tenant rather than the user's organization. We build
    a request-scoped client signed with the org's safina_ec_private_key
    column and call send through it.
    """
    from backend.safina.factory import get_safina_client_for_org
    from backend.services.transaction_service import TransactionService

    org_id = org_ids[0] if org_ids else None
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="User is not attached to any organization — cannot send transaction",
        )

    pool = get_db_pool(http_request)
    tenant_client = await get_safina_client_for_org(pool, org_id)
    try:
        base_svc = _get_service()
        tenant_service = TransactionService(
            tenant_client, base_svc._db, compliance=base_svc._compliance,
        )
        tx_unid = await tenant_service.send_transaction(
            request, validate=validate, org_id=str(org_id),
        )
        return {"tx_unid": tx_unid, "status": "pending"}
    except TransactionValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "Validation failed", "message": str(e)}
        )
    except TransactionBlockedError as e:
        # Distinct error code so the frontend can surface the AML
        # context (which rules fired, severity) — not a validation bug.
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Blocked by AML rule",
                "message": str(e),
                "triggered": e.triggered,
            },
        )
    except SafinaError as e:
        # Safina 4xx → user-error (e.g. wallet has no tokens to send, bad
        # address). Surface as 400 with a clean message so the UI can show
        # "no balance" / "invalid token" instead of a generic 502.
        sc = getattr(e, "status_code", None)
        if sc and 400 <= sc < 500:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Safina rejected the request",
                    "message": str(e),
                    "hint": (
                        "Кошелёк пуст или указанный token не привязан к нему. "
                        "Проверьте депозит через faucet и повторите."
                        if sc == 404 else None
                    ),
                },
            )
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await tenant_client.close()


# NOTE: /api/transactions/{unid}/sign and /api/transactions/{unid}/reject
# were marked deprecated since 2026-Q1 and have been removed. They bypassed
# signature_history (no append-only audit trail) and the replay-guard from
# migration 018 — keeping them around was a real security regression risk.
# The frontend has been on POST /api/signatures/{tx_unid}/{sign,reject}
# since the redesign; see routes_signatures.py.


@router.post("/sync")
async def sync_transactions(user: dict = Depends(require_roles("company_admin"))):
    """Force sync transactions from Safina API."""
    service = _get_service()
    try:
        await service.sync_transactions()
        return {"ok": True}
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))



# ==================== Batch Operations ====================

from pydantic import BaseModel


class BatchTransactionRequest(BaseModel):
    """Single transaction in a batch."""
    token: str
    to_address: str
    value: str
    info: str = ""
    json_info: dict = None


class BatchSignRequest(BaseModel):
    """Request for batch signing."""
    transaction_ids: List[str]


@router.post("/batch")
async def create_batch_transactions(
    requests: List[BatchTransactionRequest],
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user"))
):
    """
    Create multiple transactions at once. Max 50 per batch.
    
    Returns results and errors for each transaction.
    """
    if len(requests) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 transactions per batch")
    
    service = _get_service()
    results = []
    errors = []
    
    for i, req in enumerate(requests):
        try:
            send_req = SendTransactionRequest(
                token=req.token,
                to_address=req.to_address,
                value=req.value,
                info=req.info,
                json_info=req.json_info
            )
            tx_unid = await service.send_transaction(send_req, validate=True)
            results.append({"index": i, "status": "success", "tx_unid": tx_unid})
        except Exception as e:
            errors.append({"index": i, "status": "error", "message": str(e)})
    
    return {
        "total": len(requests),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/batch-sign")
async def batch_sign_transactions(
    request: BatchSignRequest,
    fastapi_request: Request,
    user: dict = Depends(require_roles("company_admin", "company_operator"))
):
    """
    Sign multiple transactions at once.

    Returns results and errors for each transaction.
    """
    if len(request.transaction_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 transactions per batch")

    service = _get_service()
    results = []
    errors = []

    # One request_id across the whole batch — lets compliance correlate
    # the audit rows in signature_history with the single triggering
    # API call. Per-row IDs would be misleading; this was one human
    # action against N transactions.
    rid = (
        getattr(fastapi_request.state, "request_id", None)
        or fastapi_request.headers.get("x-request-id")
    )

    for i, tx_id in enumerate(request.transaction_ids):
        try:
            result = await service.sign_transaction(tx_id, request_id=rid)
            results.append({"index": i, "tx_id": tx_id, "status": "success", "result": result})
        except Exception as e:
            errors.append({"index": i, "tx_id": tx_id, "status": "error", "message": str(e)})
    
    return {
        "total": len(request.transaction_ids),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }
