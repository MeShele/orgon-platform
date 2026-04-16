"""
Safina Integration endpoints — closing the API gap.

New endpoints:
- Fee estimation (transaction fee calculation by tariff)
- Address validation (crypto address format check)  
- Balance reconciliation (compare local vs Safina balances)
- Safina webhook callback (incoming notifications from Safina)
- Exchange rates (real-time crypto rates)
- Wallet lookup by UNID via Safina API
"""

import re
import hmac
import hashlib
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field

from backend.rbac import require_roles, require_any_auth
from backend.safina.errors import SafinaError

logger = logging.getLogger("orgon.api.safina_integration")

router = APIRouter(tags=["safina-integration"])


# ==================== Helpers ====================

def _get_safina_client():
    from backend.main import get_safina_client
    return get_safina_client()

def _get_wallet_service():
    from backend.main import get_wallet_service
    return get_wallet_service()

def _get_balance_service():
    from backend.main import get_balance_service
    return get_balance_service()

def _get_transaction_service():
    from backend.main import get_transaction_service
    return get_transaction_service()


# ==================== Schemas ====================

class FeeEstimateRequest(BaseModel):
    network: str = Field(..., description="Blockchain network (e.g. tron, ethereum, bitcoin)")
    token: str = Field(..., description="Token symbol (e.g. USDT_TRC20, BTC)")
    amount: str = Field(..., description="Transaction amount")
    priority: str = Field("normal", description="Priority: low, normal, high")
    tariff: str = Field("A", description="Tariff plan: A, B, or C")


class FeeEstimateResponse(BaseModel):
    network: str
    token: str
    amount: str
    network_fee: str
    platform_fee: str
    total_fee: str
    tariff: str
    priority: str
    estimated_time_seconds: int


class AddressValidationRequest(BaseModel):
    address: str = Field(..., description="Crypto address to validate")
    network: str = Field(..., description="Blockchain network")


class AddressValidationResponse(BaseModel):
    address: str
    network: str
    valid: bool
    address_type: Optional[str] = None
    error: Optional[str] = None


class ReconciliationResult(BaseModel):
    wallet_name: str
    token: str
    local_balance: str
    safina_balance: str
    difference: str
    status: str  # match, mismatch, error


# ==================== Fee Estimation ====================

# Platform fee schedules by tariff (percentage)
TARIFF_FEES = {
    "A": {"base_pct": 0.5, "min_fee": 1.0, "max_fee": 500.0},
    "B": {"base_pct": 0.3, "min_fee": 0.5, "max_fee": 300.0},
    "C": {"base_pct": 0.1, "min_fee": 0.1, "max_fee": 100.0},
}

# Estimated network fees (in USD equivalent) and confirmation times
NETWORK_FEES = {
    "tron": {"fee_usd": 1.0, "time_low": 180, "time_normal": 60, "time_high": 15},
    "ethereum": {"fee_usd": 5.0, "time_low": 600, "time_normal": 180, "time_high": 30},
    "bitcoin": {"fee_usd": 3.0, "time_low": 3600, "time_normal": 600, "time_high": 60},
    "bsc": {"fee_usd": 0.3, "time_low": 60, "time_normal": 15, "time_high": 5},
}

PRIORITY_MULTIPLIER = {"low": 0.5, "normal": 1.0, "high": 2.0}


@router.api_route("/api/transactions/estimate-fee", methods=["GET", "POST"], response_model=FeeEstimateResponse)
async def estimate_transaction_fee(
    network: str = Query(...),
    token: str = Query(...),
    amount: str = Query(...),
    priority: str = Query("normal"),
    tariff: str = Query("A"),
    user: dict = Depends(require_any_auth()),
):
    """
    Estimate transaction fee before creating a transaction.
    
    Includes both network fee and platform fee based on tariff plan.
    """
    if tariff not in TARIFF_FEES:
        raise HTTPException(400, f"Invalid tariff: {tariff}. Must be A, B, or C")
    if priority not in PRIORITY_MULTIPLIER:
        raise HTTPException(400, f"Invalid priority: {priority}. Must be low, normal, or high")

    network_lower = network.lower()
    net_info = NETWORK_FEES.get(network_lower, {"fee_usd": 2.0, "time_low": 300, "time_normal": 120, "time_high": 30})

    try:
        amount_float = float(amount)
    except ValueError:
        raise HTTPException(400, "Invalid amount format")

    # Network fee (adjusted by priority)
    network_fee = net_info["fee_usd"] * PRIORITY_MULTIPLIER[priority]

    # Platform fee (percentage of amount, clamped)
    tariff_info = TARIFF_FEES[tariff]
    platform_fee = amount_float * tariff_info["base_pct"] / 100
    platform_fee = max(tariff_info["min_fee"], min(platform_fee, tariff_info["max_fee"]))

    total_fee = network_fee + platform_fee
    time_key = f"time_{priority}"
    est_time = net_info.get(time_key, 120)

    return FeeEstimateResponse(
        network=network,
        token=token,
        amount=amount,
        network_fee=f"{network_fee:.4f}",
        platform_fee=f"{platform_fee:.4f}",
        total_fee=f"{total_fee:.4f}",
        tariff=tariff,
        priority=priority,
        estimated_time_seconds=est_time,
    )


# ==================== Address Validation ====================

# Address regex patterns per network
ADDRESS_PATTERNS = {
    "bitcoin": [
        (r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$", "P2PKH/P2SH"),
        (r"^bc1[a-z0-9]{39,59}$", "Bech32"),
    ],
    "ethereum": [
        (r"^0x[a-fA-F0-9]{40}$", "ERC20"),
    ],
    "tron": [
        (r"^T[a-zA-Z0-9]{33}$", "TRC20"),
    ],
    "bsc": [
        (r"^0x[a-fA-F0-9]{40}$", "BEP20"),
    ],
    "litecoin": [
        (r"^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$", "Legacy"),
        (r"^ltc1[a-z0-9]{39,59}$", "Bech32"),
    ],
}


@router.post("/api/addresses/validate", response_model=AddressValidationResponse)
async def validate_address(
    request: AddressValidationRequest,
    user: dict = Depends(require_any_auth()),
):
    """
    Validate cryptocurrency address format for a given network.
    
    Checks:
    - Format/regex validation
    - Network-specific rules  
    - Address type detection (P2PKH, ERC20, TRC20, etc.)
    """
    network_lower = request.network.lower()
    patterns = ADDRESS_PATTERNS.get(network_lower)

    if not patterns:
        # Unknown network — basic length check
        if len(request.address) < 20 or len(request.address) > 100:
            return AddressValidationResponse(
                address=request.address,
                network=request.network,
                valid=False,
                error=f"Address length invalid for network {request.network}",
            )
        return AddressValidationResponse(
            address=request.address,
            network=request.network,
            valid=True,
            address_type="unknown",
        )

    for pattern, addr_type in patterns:
        if re.match(pattern, request.address):
            return AddressValidationResponse(
                address=request.address,
                network=request.network,
                valid=True,
                address_type=addr_type,
            )

    return AddressValidationResponse(
        address=request.address,
        network=request.network,
        valid=False,
        error=f"Address does not match any known {request.network} format",
    )


# ==================== Balance Reconciliation ====================

@router.get("/api/wallets/reconciliation")
async def reconcile_balances(
    wallet_name: Optional[str] = None,
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
):
    """
    Compare local cached balances with Safina API balances.
    
    Identifies discrepancies for audit and troubleshooting.
    If wallet_name is provided, reconciles only that wallet.
    Otherwise reconciles all wallets.
    """
    safina = _get_safina_client()
    balance_service = _get_balance_service()

    if not safina:
        raise HTTPException(503, "Safina client not available")

    results: List[dict] = []

    try:
        if wallet_name:
            wallets_to_check = [wallet_name]
        else:
            wallets = await safina.get_wallets()
            wallets_to_check = [w.name for w in wallets]

        for wname in wallets_to_check:
            try:
                safina_tokens = await safina.get_wallet_tokens(wname)
                local_balances = await balance_service.get_wallet_balances(wname) if balance_service else {}

                for token in safina_tokens:
                    token_symbol = getattr(token, "token", getattr(token, "symbol", "unknown"))
                    safina_bal = str(getattr(token, "balance", getattr(token, "value", "0")))

                    local_bal = "0"
                    if isinstance(local_balances, list):
                        for lb in local_balances:
                            if isinstance(lb, dict) and lb.get("token") == token_symbol:
                                local_bal = str(lb.get("balance", "0"))
                                break
                    elif isinstance(local_balances, dict):
                        local_bal = str(local_balances.get(token_symbol, "0"))

                    try:
                        diff = float(safina_bal) - float(local_bal)
                        status = "match" if abs(diff) < 0.0001 else "mismatch"
                    except (ValueError, TypeError):
                        diff = 0
                        status = "error"

                    results.append({
                        "wallet_name": wname,
                        "token": token_symbol,
                        "local_balance": local_bal,
                        "safina_balance": safina_bal,
                        "difference": f"{diff:.8f}",
                        "status": status,
                    })
            except Exception as e:
                results.append({
                    "wallet_name": wname,
                    "token": "ALL",
                    "local_balance": "N/A",
                    "safina_balance": "N/A",
                    "difference": "N/A",
                    "status": f"error: {str(e)}",
                })

    except SafinaError as e:
        raise HTTPException(502, f"Safina API error: {e}")

    summary = {
        "total_checked": len(results),
        "matches": sum(1 for r in results if r["status"] == "match"),
        "mismatches": sum(1 for r in results if r["status"] == "mismatch"),
        "errors": sum(1 for r in results if r["status"].startswith("error")),
    }

    return {
        "reconciliation_time": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "details": results,
    }


# ==================== Safina Webhook Callback ====================

SAFINA_WEBHOOK_SECRET = None  # Set from config/env

@router.post("/api/webhooks/safina/callback")
async def safina_webhook_callback(request: Request):
    """
    Receive webhook callbacks from Safina API.
    
    Handles events:
    - transaction.confirmed
    - transaction.failed
    - wallet.balance_updated
    - compliance.alert
    
    Verifies HMAC signature if webhook secret is configured.
    """
    from backend.config import get_config
    config = get_config()
    webhook_secret = getattr(config, "SAFINA_WEBHOOK_SECRET", None) or SAFINA_WEBHOOK_SECRET

    body = await request.body()

    # Verify signature if secret is configured
    if webhook_secret:
        signature = request.headers.get("X-Safina-Signature", "")
        expected = hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, f"sha256={expected}"):
            logger.warning("Invalid Safina webhook signature")
            raise HTTPException(401, "Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")

    event_type = payload.get("event", "unknown")
    data = payload.get("data", {})

    logger.info(f"Safina webhook received: {event_type}")

    try:
        if event_type == "transaction.confirmed":
            await _handle_tx_confirmed(data)
        elif event_type == "transaction.failed":
            await _handle_tx_failed(data)
        elif event_type == "wallet.balance_updated":
            await _handle_balance_updated(data)
        elif event_type == "compliance.alert":
            await _handle_compliance_alert(data)
        else:
            logger.info(f"Unhandled Safina webhook event: {event_type}")

    except Exception as e:
        logger.error(f"Error processing Safina webhook {event_type}: {e}")
        # Return 200 to avoid retries for processing errors
        return {"status": "error", "message": str(e)}

    return {"status": "processed", "event": event_type}


async def _handle_tx_confirmed(data: dict):
    """Handle transaction confirmation from Safina."""
    from backend.database.db import get_db
    db = get_db()
    tx_unid = data.get("transaction_unid") or data.get("tx_unid")
    confirmations = data.get("confirmations", 0)

    if tx_unid:
        db.execute(
            "UPDATE transactions SET status = 'confirmed', confirmations = ? WHERE unid = ?",
            (confirmations, tx_unid),
        )
        logger.info(f"Transaction {tx_unid} confirmed ({confirmations} confirmations)")

        # Broadcast via WebSocket
        try:
            from backend.websocket_manager import ws_manager
            await ws_manager.broadcast({
                "type": "transaction.confirmed",
                "data": {"unid": tx_unid, "confirmations": confirmations},
            })
        except Exception:
            pass


async def _handle_tx_failed(data: dict):
    """Handle transaction failure from Safina."""
    from backend.database.db import get_db
    db = get_db()
    tx_unid = data.get("transaction_unid") or data.get("tx_unid")
    reason = data.get("reason", "Unknown")

    if tx_unid:
        db.execute(
            "UPDATE transactions SET status = 'failed', error_message = ? WHERE unid = ?",
            (reason, tx_unid),
        )
        logger.warning(f"Transaction {tx_unid} failed: {reason}")


async def _handle_balance_updated(data: dict):
    """Handle balance update notification from Safina."""
    wallet_name = data.get("wallet_name") or data.get("wallet")
    if wallet_name:
        # Trigger balance sync for the wallet
        try:
            balance_service = _get_balance_service()
            if balance_service:
                await balance_service.sync_wallet_balances(wallet_name)
                logger.info(f"Balance synced for wallet {wallet_name}")
        except Exception as e:
            logger.error(f"Failed to sync balance for {wallet_name}: {e}")


async def _handle_compliance_alert(data: dict):
    """Handle compliance alert from Safina."""
    logger.warning(f"Compliance alert from Safina: {data}")
    # Store alert for review
    try:
        from backend.database.db import get_db
        db = get_db()
        db.execute(
            "INSERT INTO audit_log (action, details, created_at) VALUES (?, ?, ?)",
            ("compliance_alert", str(data), datetime.now(timezone.utc).isoformat()),
        )
    except Exception as e:
        logger.error(f"Failed to store compliance alert: {e}")


# ==================== Exchange Rates (Crypto) ====================

@router.get("/api/rates")
async def get_exchange_rates(
    tokens: str = Query("BTC,ETH,USDT,TRX", description="Comma-separated token symbols"),
    currency: str = Query("USD", description="Fiat currency for conversion"),
    user: dict = Depends(require_any_auth()),
):
    """
    Get real-time exchange rates for crypto tokens.
    
    Uses the PriceFeedService with caching.
    Returns rates in the specified fiat currency.
    """
    try:
        from backend.services.price_feed_service import PriceFeedService
        price_service = PriceFeedService()
        
        token_list = [t.strip().upper() for t in tokens.split(",") if t.strip()]
        
        rates = {}
        for token in token_list:
            try:
                price = await price_service.get_price(token, currency.lower())
                if price is not None:
                    rates[token] = {
                        "price": price,
                        "currency": currency.upper(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            except Exception:
                rates[token] = {"price": None, "currency": currency.upper(), "error": "Price unavailable"}

        await price_service.close()
        return {"rates": rates, "currency": currency.upper()}
    except Exception as e:
        raise HTTPException(502, f"Price feed error: {e}")


# ==================== Transactions by EC (signing entity) ====================

@router.get("/api/transactions/by-ec")
async def get_transactions_by_ec(
    user: dict = Depends(require_roles("company_admin", "company_operator")),
):
    """
    Get transactions that require signing by the current EC (entity certificate).
    
    Maps to Safina API: GET /ece/tx_by_ec
    Returns transactions where the current signer is in the slist.
    """
    safina = _get_safina_client()
    if not safina:
        raise HTTPException(503, "Safina client not available")

    try:
        # Use the pending signatures which filters by current EC
        pending = await safina.get_pending_signatures()
        return {
            "transactions": [p.dict() if hasattr(p, 'dict') else p for p in pending],
            "count": len(pending),
        }
    except SafinaError as e:
        raise HTTPException(502, f"Safina API error: {e}")
