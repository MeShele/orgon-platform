"""Billing API compatibility routes (non-v1 prefix).

Frontend may call /api/billing/plans and /api/billing/usage.
The real billing routes live at /api/v1/billing/*.
These endpoints return mock data so the billing page works.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/billing", tags=["Billing (compat)"])


@router.get("/plans")
async def get_plans_compat():
    """Return mock billing plans."""
    return [
        {
            "id": "starter",
            "name": "Starter",
            "monthly_price": 0,
            "yearly_price": 0,
            "currency": "USD",
            "features": ["Up to 100 transactions/month", "1 wallet", "Email support"],
            "is_active": True,
        },
        {
            "id": "professional",
            "name": "Professional",
            "monthly_price": 99,
            "yearly_price": 990,
            "currency": "USD",
            "features": ["Unlimited transactions", "10 wallets", "Priority support", "API access"],
            "is_active": True,
        },
        {
            "id": "enterprise",
            "name": "Enterprise",
            "monthly_price": 499,
            "yearly_price": 4990,
            "currency": "USD",
            "features": ["Unlimited everything", "White-label", "Dedicated support", "Custom integrations"],
            "is_active": True,
        },
    ]


@router.get("/usage")
async def get_usage_compat():
    """Return mock usage data."""
    return {
        "current_plan": "starter",
        "billing_cycle": "monthly",
        "usage": {
            "transactions": {"used": 0, "limit": 100},
            "wallets": {"used": 0, "limit": 1},
            "api_calls": {"used": 0, "limit": 1000},
        },
        "next_invoice_date": None,
        "outstanding_balance": 0,
    }
