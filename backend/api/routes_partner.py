"""
Partner API Routes
External API for B2B partners (authenticated via API key)
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime, timezone

# Import schemas
from backend.api.schemas_b2b import (
    # Wallet schemas
    WalletCreateRequest, WalletResponse, WalletListResponse,
    # Transaction schemas
    TransactionCreateRequest, TransactionResponse, TransactionListResponse,
    # Signature schemas
    SignatureApproveRequest, SignatureRejectRequest,
    PendingSignaturesResponse, SignatureHistoryResponse,
    # Network & Token schemas
    NetworkListResponse, TokenListResponse,
    # Pagination
    PaginationParams, PaginationMeta,
    # Error
    ErrorResponse,
)

# Import services (not used for instantiation, only for type hints)
from backend.services.wallet_service import WalletService
from backend.services.transaction_service import TransactionService
from backend.services.signature_service import SignatureService, DuplicateSignatureError
from backend.services.network_service import NetworkService
from backend.services.audit_service import AuditService
from backend.services.webhook_service import WebhookService

# Import middleware helpers
from backend.api.middleware_b2b import get_partner_from_request


# Create router
router = APIRouter(prefix="/api/v1/partner", tags=["Partner API"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_wallet_service(request: Request) -> WalletService:
    """Get WalletService instance from app state."""
    return request.app.state.wallet_service


async def get_transaction_service(request: Request) -> TransactionService:
    """Get TransactionService instance from app state."""
    return request.app.state.transaction_service


async def get_signature_service(request: Request) -> SignatureService:
    """Get SignatureService instance from app state."""
    return request.app.state.signature_service


async def get_network_service(request: Request) -> NetworkService:
    """Get NetworkService instance from app state."""
    return request.app.state.network_service


async def get_audit_service(request: Request) -> AuditService:
    """Get AuditService instance from app state."""
    return request.app.state.audit_service


async def get_webhook_service(request: Request) -> WebhookService:
    """Get WebhookService instance from app state."""
    if not hasattr(request.app.state, "webhook_service"):
        return None  # Webhooks not enabled
    return request.app.state.webhook_service


# ============================================================================
# TENANCY HELPER
# ============================================================================

async def _partner_org_ids(request: Request, partner: dict) -> list | None:
    """Return the organization IDs visible to a partner-authenticated request.

    Returns:
        - `None` for internal/dashboard callers (JWT auth) — no scoping.
        - `[<uuid>]` for an API-key partner that has been linked to an
          organization (see migration 017_partner_org_link.sql).
        - `[]`     for an API-key partner that exists but isn't linked yet —
          treated as "sees nothing", which is the safe default.
    """
    if partner.get("partner_id") is None:
        return None  # internal / JWT dashboard

    db = request.app.state.db
    row = await db.fetchrow(
        "SELECT organization_id FROM partners WHERE id = $1",
        params=(partner["partner_id"],),
    )
    if not row or not row.get("organization_id"):
        return []
    return [row["organization_id"]]


# ============================================================================
# WALLET ENDPOINTS
# ============================================================================

@router.post(
    "/wallets",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Wallet",
    description="Create a new multisig wallet on specified network.",
    responses={
        201: {"description": "Wallet created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "Wallet name already exists"},
    }
)
async def create_wallet(
    request: Request,
    wallet_data: WalletCreateRequest,
    wallet_service: WalletService = Depends(get_wallet_service),
    audit_service: AuditService = Depends(get_audit_service),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    Create a new wallet for partner.
    
    **Authentication:** Requires valid API key + secret.
    
    **Request Body:**
    - `name`: Unique wallet name (alphanumeric, hyphens, underscores)
    - `network_id`: Network ID (5000=Tron mainnet, 5010=Tron Nile testnet)
    - `wallet_type`: Wallet type (1=multisig)
    - `label`: Optional custom label
    
    **Returns:** Created wallet details.
    """
    partner = get_partner_from_request(request)
    
    try:
        # Create wallet via Safina API
        wallet = await wallet_service.create_wallet(
            name=wallet_data.name,
            network_id=wallet_data.network_id,
            wallet_type=wallet_data.wallet_type,
            label=wallet_data.label
        )
        
        # Log action to audit trail
        await audit_service.log_wallet_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="wallet.create",
            wallet_name=wallet_data.name,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            changes={
                "before": None,
                "after": {
                    "name": wallet_data.name,
                    "network_id": wallet_data.network_id,
                    "wallet_type": wallet_data.wallet_type,
                    "label": wallet_data.label
                }
            },
            result="success"
        )
        
        # Emit webhook event
        if webhook_service:
            await webhook_service.emit_event(
                partner_id=partner["partner_id"],
                event_type="wallet.created",
                payload={
                    "wallet_name": wallet["name"],
                    "network_id": wallet["network"],
                    "wallet_type": wallet.get("wallet_type", 1),
                    "address": wallet.get("addr", ""),
                    "label": wallet.get("label"),
                    "created_at": wallet["created_at"]
                }
            )
        
        return WalletResponse(
            name=wallet["name"],
            network_id=wallet["network"],
            wallet_type=wallet.get("wallet_type", 1),
            address=wallet.get("addr"),
            label=wallet.get("label"),
            is_favorite=bool(wallet.get("is_favorite", 0)),
            tokens=[],  # TODO: Fetch token balances
            created_at=wallet["created_at"],
            synced_at=wallet.get("synced_at")
        )
    
    except ValueError as e:
        # Log failed action
        await audit_service.log_wallet_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="wallet.create",
            wallet_name=wallet_data.name,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="failure",
            error_message=str(e)
        )
        
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "wallet_exists", "message": str(e)}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_request", "message": str(e)}
            )


@router.get(
    "/wallets",
    response_model=WalletListResponse,
    summary="List Wallets",
    description="Get paginated list of wallets for partner.",
)
async def list_wallets(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    network_id: Optional[int] = Query(None, description="Filter by network ID"),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """
    List all wallets for authenticated partner.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `limit`: Max results per page (1-100, default 50)
    - `offset`: Number of results to skip (default 0)
    - `network_id`: Optional filter by network ID
    
    **Returns:** Paginated wallet list.
    """
    partner = get_partner_from_request(request)
    org_ids = await _partner_org_ids(request, partner)

    wallets_data = await wallet_service.list_wallets(
        network_id=network_id,
        limit=limit + 1,  # Fetch one extra to check has_more
        offset=offset,
        org_ids=org_ids,
    )

    # Check if more results exist
    has_more = len(wallets_data) > limit
    wallets_data = wallets_data[:limit]  # Trim to limit

    # Convert to response models
    wallets = [
        WalletResponse(
            name=w["name"],
            network_id=w["network"],
            wallet_type=w.get("wallet_type", 1),
            address=w.get("addr"),
            label=w.get("label"),
            is_favorite=bool(w.get("is_favorite", 0)),
            tokens=[],  # TODO: Fetch token balances
            created_at=w["created_at"],
            synced_at=w.get("synced_at")
        )
        for w in wallets_data
    ]

    total = await wallet_service.count_wallets(network_id=network_id, org_ids=org_ids)
    
    return WalletListResponse(
        wallets=wallets,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more
        )
    )


@router.get(
    "/wallets/{wallet_name}",
    response_model=WalletResponse,
    summary="Get Wallet Details",
    description="Get detailed information about a specific wallet.",
)
async def get_wallet(
    request: Request,
    wallet_name: str,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """
    Get wallet details by name.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `wallet_name`: Wallet name
    
    **Returns:** Wallet details with token balances.
    """
    partner = get_partner_from_request(request)
    org_ids = await _partner_org_ids(request, partner)

    wallet = await wallet_service.get_wallet_by_name(wallet_name, org_ids=org_ids)

    if not wallet:
        # Returns 404 even when the wallet exists but is in a different org —
        # we do not leak existence across tenants.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "wallet_not_found", "message": f"Wallet '{wallet_name}' not found"}
        )

    # Fetch token balances
    # TODO: Implement in WalletService
    tokens = []
    
    return WalletResponse(
        name=wallet["name"],
        network_id=wallet["network"],
        wallet_type=wallet.get("wallet_type", 1),
        address=wallet.get("addr"),
        label=wallet.get("label"),
        is_favorite=bool(wallet.get("is_favorite", 0)),
        tokens=tokens,
        created_at=wallet["created_at"],
        synced_at=wallet.get("synced_at")
    )


# ============================================================================
# TRANSACTION ENDPOINTS
# ============================================================================

@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Transaction",
    description="Create and send a transaction (requires signatures).",
)
async def send_transaction(
    request: Request,
    tx_data: TransactionCreateRequest,
    transaction_service: TransactionService = Depends(get_transaction_service),
    audit_service: AuditService = Depends(get_audit_service),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    Send a transaction from wallet.
    
    **Authentication:** Requires valid API key + secret.
    
    **Request Body:**
    - `wallet_name`: Source wallet name
    - `token`: Token symbol (TRX, USDT, etc.)
    - `to_address`: Destination address
    - `amount`: Amount to send (decimal string)
    - `memo`: Optional memo/note
    
    **Returns:** Created transaction with pending signature status.
    """
    partner = get_partner_from_request(request)
    
    try:
        # Send transaction via Safina API
        tx = await transaction_service.send_transaction(
            wallet_name=tx_data.wallet_name,
            token=tx_data.token,
            to_address=tx_data.to_address,
            amount=tx_data.amount
        )
        
        # Log action to audit trail
        await audit_service.log_transaction_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="tx.send",
            tx_unid=tx["unid"],
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="success",
            metadata={
                "wallet_name": tx_data.wallet_name,
                "token": tx_data.token,
                "to_address": tx_data.to_address,
                "amount": tx_data.amount,
                "memo": tx_data.memo
            }
        )
        
        # Emit webhook event
        if webhook_service:
            await webhook_service.emit_event(
                partner_id=partner["partner_id"],
                event_type="transaction.created",
                payload={
                    "unid": tx["unid"],
                    "wallet_name": tx_data.wallet_name,
                    "token": tx_data.token,
                    "to_address": tx_data.to_address,
                    "amount": tx_data.amount,
                    "status": tx["status"],
                    "created_at": tx["created_at"]
                }
            )
        
        return TransactionResponse(
            unid=tx["unid"],
            wallet_name=tx_data.wallet_name,
            token=tx_data.token,
            to_address=tx_data.to_address,
            amount=tx_data.amount,
            status=tx["status"],
            tx_hash=tx.get("tx_hash"),
            min_signatures=tx.get("min_sign", 1),
            current_signatures=0,  # TODO: Get from signature service
            memo=tx_data.memo,
            created_at=tx["created_at"],
            confirmed_at=tx.get("confirmed_at")
        )
    
    except ValueError as e:
        # Log failed action
        await audit_service.log_transaction_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="tx.send",
            tx_unid="FAILED",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="failure",
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "transaction_failed", "message": str(e)}
        )


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    summary="List Transactions",
    description="Get paginated list of transactions.",
)
async def list_transactions(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    wallet_name: Optional[str] = Query(None, description="Filter by wallet"),
    status: Optional[str] = Query(None, description="Filter by status"),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """
    List transactions for authenticated partner.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `limit`: Max results per page (1-100)
    - `offset`: Pagination offset
    - `wallet_name`: Optional filter by wallet
    - `status`: Optional filter by status (pending, confirmed, failed)
    
    **Returns:** Paginated transaction list.
    """
    partner = get_partner_from_request(request)
    org_ids = await _partner_org_ids(request, partner)

    txs_data = await transaction_service.list_transactions(
        wallet_name=wallet_name,
        status=status,
        limit=limit + 1,
        offset=offset,
        org_ids=org_ids,
    )

    has_more = len(txs_data) > limit
    txs_data = txs_data[:limit]
    
    # Convert to response models
    transactions = [
        TransactionResponse(
            unid=tx["unid"],
            wallet_name=tx["wallet_name"],
            token=tx["token_name"],
            to_address=tx["to_addr"],
            amount=tx["value"],
            status=tx["status"],
            tx_hash=tx.get("tx_hash"),
            min_signatures=tx.get("min_sign", 1),
            current_signatures=0,  # TODO: Get from signature service
            memo=None,  # TODO: Add memo field to transactions table
            created_at=tx["created_at"],
            confirmed_at=tx.get("updated_at") if tx["status"] == "confirmed" else None
        )
        for tx in txs_data
    ]
    
    total = await transaction_service.count_transactions(
        wallet_name=wallet_name,
        status=status,
        org_ids=org_ids,
    )
    
    return TransactionListResponse(
        transactions=transactions,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more
        )
    )


@router.get(
    "/transactions/{unid}",
    response_model=TransactionResponse,
    summary="Get Transaction Details",
    description="Get detailed information about a specific transaction.",
)
async def get_transaction(
    request: Request,
    unid: str,
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """
    Get transaction details by UNID.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `unid`: Transaction UNID
    
    **Returns:** Transaction details.
    """
    partner = get_partner_from_request(request)
    org_ids = await _partner_org_ids(request, partner)

    tx = await transaction_service.get_transaction(unid, org_ids=org_ids)

    if not tx:
        # 404 also when the row exists in a different org — no cross-tenant leak.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "transaction_not_found", "message": f"Transaction '{unid}' not found"}
        )
    
    return TransactionResponse(
        unid=tx["unid"],
        wallet_name=tx["wallet_name"],
        token=tx["token_name"],
        to_address=tx["to_addr"],
        amount=tx["value"],
        status=tx["status"],
        tx_hash=tx.get("tx_hash"),
        min_signatures=tx.get("min_sign", 1),
        current_signatures=0,  # TODO: Get from signature service
        memo=None,
        created_at=tx["created_at"],
        confirmed_at=tx.get("updated_at") if tx["status"] == "confirmed" else None
    )


# ============================================================================
# SIGNATURE ENDPOINTS
# ============================================================================

@router.post(
    "/transactions/{unid}/sign",
    status_code=status.HTTP_200_OK,
    summary="Approve Transaction",
    description="Approve a pending transaction signature.",
)
async def approve_signature(
    request: Request,
    unid: str,
    signature_service: SignatureService = Depends(get_signature_service),
    audit_service: AuditService = Depends(get_audit_service),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    Approve (sign) a pending transaction.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `unid`: Transaction UNID
    
    **Returns:** Success message.
    """
    partner = get_partner_from_request(request)
    
    try:
        result = await signature_service.sign_transaction(
            tx_unid=unid,
            user_address=partner["ec_address"],
        )

        await audit_service.log_signature_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="signature.approve",
            tx_unid=unid,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="success"
        )

        if webhook_service:
            await webhook_service.emit_event(
                partner_id=partner["partner_id"],
                event_type="signature.approved",
                payload={
                    "unid": unid,
                    "approved_by": partner["ec_address"],
                    "approved_at": datetime.now(timezone.utc).isoformat()
                }
            )

        return {
            "success": True,
            "message": "Signature approved",
            "unid": unid
        }

    except DuplicateSignatureError as e:
        await audit_service.log_signature_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="signature.approve",
            tx_unid=unid,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="duplicate",
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_signature", "message": str(e)},
        )

    except ValueError as e:
        await audit_service.log_signature_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="signature.approve",
            tx_unid=unid,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="failure",
            error_message=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "approval_failed", "message": str(e)}
        )


@router.post(
    "/transactions/{unid}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject Transaction",
    description="Reject a pending transaction signature.",
)
async def reject_signature(
    request: Request,
    unid: str,
    reject_data: SignatureRejectRequest,
    signature_service: SignatureService = Depends(get_signature_service),
    audit_service: AuditService = Depends(get_audit_service),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    Reject a pending transaction.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `unid`: Transaction UNID
    
    **Request Body:**
    - `reason`: Optional rejection reason
    
    **Returns:** Success message.
    """
    partner = get_partner_from_request(request)
    
    try:
        result = await signature_service.reject_transaction(
            tx_unid=unid,
            reason=reject_data.reason,
            user_address=partner["ec_address"],
        )

        await audit_service.log_signature_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="signature.reject",
            tx_unid=unid,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="success"
        )

        if webhook_service:
            await webhook_service.emit_event(
                partner_id=partner["partner_id"],
                event_type="signature.rejected",
                payload={
                    "unid": unid,
                    "rejected_by": partner["ec_address"],
                    "reason": reject_data.reason,
                    "rejected_at": datetime.now(timezone.utc).isoformat()
                }
            )

        return {
            "success": True,
            "message": "Signature rejected",
            "unid": unid,
            "reason": reject_data.reason
        }

    except DuplicateSignatureError as e:
        await audit_service.log_signature_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="signature.reject",
            tx_unid=unid,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="duplicate",
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_signature", "message": str(e)},
        )

    except ValueError as e:
        # Log failed action
        await audit_service.log_signature_action(
            partner_id=partner["partner_id"],
            user_id=partner["ec_address"],
            action="signature.reject",
            tx_unid=unid,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            result="failure",
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "rejection_failed", "message": str(e)}
        )


@router.get(
    "/signatures/pending",
    response_model=PendingSignaturesResponse,
    summary="Get Pending Signatures",
    description="Get list of transactions awaiting partner signature.",
)
async def get_pending_signatures(
    request: Request,
    signature_service: SignatureService = Depends(get_signature_service)
):
    """
    Get pending signatures for authenticated partner.
    
    **Authentication:** Requires valid API key + secret.
    
    **Returns:** List of transactions awaiting signature.
    """
    partner = get_partner_from_request(request)
    
    # Fetch pending signatures
    # TODO: Implement in SignatureService
    pending = []
    
    return PendingSignaturesResponse(
        pending=pending,
        count=len(pending)
    )


# ============================================================================
# NETWORK & TOKEN INFO ENDPOINTS
# ============================================================================

@router.get(
    "/networks",
    response_model=NetworkListResponse,
    summary="Get Supported Networks",
    description="Get list of supported blockchain networks.",
)
async def get_networks(
    request: Request,
    network_service: NetworkService = Depends(get_network_service)
):
    """
    Get supported networks.
    
    **Authentication:** Requires valid API key + secret.
    
    **Returns:** List of supported networks.
    """
    partner = get_partner_from_request(request)
    
    # Fetch networks
    networks_data = await network_service.list_networks()
    
    # Convert to response models
    from backend.api.schemas_b2b import NetworkInfo
    networks = [
        NetworkInfo(
            network_id=n["network_id"],
            name=n["name"],
            chain=n["chain"],
            is_testnet=n["is_testnet"]
        )
        for n in networks_data
    ]
    
    return NetworkListResponse(networks=networks)


@router.get(
    "/tokens-info",
    response_model=TokenListResponse,
    summary="Get Token Information",
    description="Get list of supported tokens with commission info.",
)
async def get_tokens_info(
    request: Request,
    network_service: NetworkService = Depends(get_network_service)
):
    """
    Get token information including platform commission.
    
    **Authentication:** Requires valid API key + secret.
    
    **Returns:** List of supported tokens with commission rates.
    """
    partner = get_partner_from_request(request)
    
    # Fetch token info from Safina API
    try:
        tokens_obj = await network_service.get_tokens_info()
        
        # Convert to response models
        from backend.api.schemas_b2b import TokenInfo
        tokens = [
            TokenInfo(
                token=t.token,
                name=t.name,
                network_id=t.network_id,
                commission_percent=float(t.commission_percent) if t.commission_percent else 0.0,
                min_amount=float(t.min_amount) if t.min_amount else None
            )
            for t in tokens_obj
        ]
    except Exception:
        # If tokens info not available, return empty list
        tokens = []
    
    return TokenListResponse(tokens=tokens)
