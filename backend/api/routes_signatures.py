"""Signature management endpoints."""

from fastapi import APIRouter, HTTPException, Request
from fastapi import Depends
from pydantic import BaseModel

from backend.safina.errors import SafinaError

from backend.rbac import require_roles
from backend.dependencies import get_user_org_ids, get_db_pool

router = APIRouter(prefix="/api/signatures", tags=["signatures"])


class RejectRequest(BaseModel):
    """Request body for rejecting a transaction."""
    reason: str = ""


def _get_signature_service():
    """Get SignatureService instance."""
    from backend.main import get_signature_service
    return get_signature_service()


@router.get("/pending")
async def get_pending_signatures(user_address: str | None = None, user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor"))):
    """
    Get transactions awaiting signature.

    Args:
        user_address: Optional EC address filter (uses signer address if not provided)

    Returns:
        List of pending signature requests
    """
    service = _get_signature_service()
    try:
        pending = await service.get_pending_signatures(user_address)
        return [p.model_dump() for p in pending]
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pending signatures: {e}"
        )


@router.get("/history")
async def get_signature_history(
    user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor")),
    user_address: str | None = None,
    limit: int = 50
):
    """
    Get history of signed transactions.

    Args:
        user_address: Optional EC address filter
        limit: Maximum number of transactions (default 50)

    Returns:
        List of signed transactions
    """
    service = _get_signature_service()
    try:
        history = await service.get_signed_transactions_history(user_address, limit)
        return history
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch signature history: {e}"
        )


@router.get("/{tx_unid}/status")
async def get_signature_status(tx_unid: str, user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor"))):
    """
    Get detailed signature status for a transaction.

    Args:
        tx_unid: Transaction unique ID

    Returns:
        Signature status with signed/waiting lists and progress
    """
    service = _get_signature_service()
    try:
        status = await service.get_signature_status(tx_unid)
        return status
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch signature status: {e}"
        )


@router.get("/{tx_unid}/details")
async def get_transaction_details(tx_unid: str, user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor"))):
    """
    Get full transaction details including signature status.

    Args:
        tx_unid: Transaction unique ID

    Returns:
        Transaction info with signature status, or 404 if not found
    """
    service = _get_signature_service()
    try:
        details = await service.get_transaction_details(tx_unid)
        if not details:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return details
    except HTTPException:
        raise
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch transaction details: {e}"
        )


@router.post("/{tx_unid}/sign")
async def sign_transaction(
    tx_unid: str,
    http_request: Request,
    user_address: str | None = None,
    user: dict = Depends(require_roles("company_admin", "company_operator")),
    org_ids: list = Depends(get_user_org_ids),
):
    """Sign a transaction using the caller's tenant EC key.

    Per-tenant signer matters here even more than at create-wallet:
    Safina rejects /tx_sign with an EC that didn't create the wallet,
    so the signature MUST come from the tenant's own key. The legacy
    singleton service is bound to the global env signer and would
    sign as the platform root tenant.
    """
    from backend.safina.factory import get_safina_client_for_org
    from backend.services.signature_service import SignatureService, DuplicateSignatureError

    org_id = org_ids[0] if org_ids else None
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="User is not attached to any organization — cannot sign",
        )

    pool = get_db_pool(http_request)
    tenant_client = await get_safina_client_for_org(pool, org_id)
    try:
        base_svc = _get_signature_service()
        tenant_service = SignatureService(
            tenant_client, base_svc._db, telegram_notifier=base_svc._telegram,
        )
        result = await tenant_service.sign_transaction(
            tx_unid,
            user_address,
            request_id=getattr(http_request.state, "request_id", None),
        )
        return {
            "ok": True,
            "message": f"Transaction {tx_unid} signed successfully",
            "result": result,
        }
    except DuplicateSignatureError as e:
        raise HTTPException(status_code=409, detail={"error": "duplicate_signature", "message": str(e)})
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sign transaction: {e}",
        )
    finally:
        await tenant_client.close()


@router.post("/{tx_unid}/reject")
async def reject_transaction(
    tx_unid: str,
    request: RejectRequest,
    http_request: Request,
    user_address: str | None = None,
    user: dict = Depends(require_roles("company_admin", "company_operator")),
):
    """
    Reject a transaction.

    Args:
        tx_unid: Transaction unique ID
        request: Rejection details (reason)
        user_address: Optional rejector address (for logging)

    Returns:
        Success confirmation
    """
    from backend.services.signature_service import DuplicateSignatureError
    service = _get_signature_service()
    try:
        result = await service.reject_transaction(
            tx_unid,
            request.reason,
            user_address,
            request_id=getattr(http_request.state, "request_id", None),
        )
        return {
            "ok": True,
            "message": f"Transaction {tx_unid} rejected",
            "result": result
        }
    except DuplicateSignatureError as e:
        raise HTTPException(status_code=409, detail={"error": "duplicate_signature", "message": str(e)})
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject transaction: {e}"
        )


@router.get("/stats")
async def get_signature_statistics(user: dict = Depends(require_roles("company_admin", "company_operator", "company_auditor"))):
    """
    Get signature statistics for monitoring.

    Returns:
        Counts of signed/rejected transactions
    """
    service = _get_signature_service()
    try:
        stats = await service.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get signature statistics: {e}"
        )
