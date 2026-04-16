"""Fiat API endpoints — On-ramp/Off-ramp."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from uuid import UUID
from decimal import Decimal
from backend.services.fiat_service import FiatService
from backend.dependencies import get_current_user, get_db_pool
from backend.rbac import require_roles

router = APIRouter(prefix="/api/v1/fiat", tags=["Fiat"])

async def get_fiat_service(pool = Depends(get_db_pool)) -> FiatService:
    return FiatService(pool)

# ==================== On-Ramp/Off-Ramp ====================

@router.post("/onramp", status_code=status.HTTP_201_CREATED)
async def create_onramp(
    org_id: UUID, fiat_amount: float, fiat_currency: str,
    crypto_currency: str, payment_method: str,
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    service: FiatService = Depends(get_fiat_service)
):
    """Buy crypto with fiat."""
    txn = await service.create_onramp_transaction(
        org_id, UUID(str(user['id'])),
        Decimal(str(fiat_amount)), fiat_currency, crypto_currency, payment_method
    )
    return txn

@router.post("/offramp", status_code=status.HTTP_201_CREATED)
async def create_offramp(
    org_id: UUID, crypto_amount: float, crypto_currency: str,
    fiat_currency: str, bank_account_id: UUID,
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    service: FiatService = Depends(get_fiat_service)
):
    """Sell crypto for fiat."""
    txn = await service.create_offramp_transaction(
        org_id, UUID(str(user['id'])),
        Decimal(str(crypto_amount)), crypto_currency, fiat_currency, bank_account_id
    )
    return txn

@router.get("/transactions")
async def get_transactions(
    org_id: UUID = Query(...),
    limit: int = Query(50, le=100),
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    service: FiatService = Depends(get_fiat_service)
):
    """Get fiat transactions."""
    txns = await service.get_fiat_transactions(org_id, UUID(str(user['id'])), limit)
    return txns

@router.put("/transactions/{txn_id}/status")
async def update_transaction_status(
    txn_id: UUID, status: str, gateway_txn_id: Optional[str] = None,
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    service: FiatService = Depends(get_fiat_service)
):
    """Update transaction status."""
    txn = await service.update_transaction_status(txn_id, status, gateway_txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn

# ==================== Bank Accounts ====================

@router.post("/bank-accounts", status_code=status.HTTP_201_CREATED)
async def add_bank_account(
    org_id: UUID, account_holder_name: str, account_number_last4: str,
    bank_country: str, currency: str = "USD",
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    service: FiatService = Depends(get_fiat_service)
):
    """Add bank account."""
    account = await service.add_bank_account(
        org_id, UUID(str(user['id'])),
        account_holder_name, account_number_last4, bank_country, currency
    )
    return account

@router.get("/bank-accounts")
async def get_bank_accounts(
    org_id: UUID = Query(...),
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    service: FiatService = Depends(get_fiat_service)
):
    """Get bank accounts."""
    accounts = await service.get_bank_accounts(org_id, UUID(str(user['id'])))
    return accounts

# ==================== Exchange Rates ====================

@router.get("/rates/{crypto}/{fiat}")
async def get_rate(
    crypto: str, fiat: str,
    user: dict = Depends(require_roles("company_admin", "company_operator", "end_user")),
    service: FiatService = Depends(get_fiat_service)
):
    """Get exchange rate."""
    rate = await service.get_exchange_rate(crypto.upper(), fiat.upper())
    return {"crypto": crypto, "fiat": fiat, "rate": rate}
