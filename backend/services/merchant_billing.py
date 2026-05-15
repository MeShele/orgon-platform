"""Merchant billing — usage counters + plan limits + enforcement.

Three concerns wired through one module:

1. `record_api_call(merchant_id)` is called from the HMAC middleware
   on every successful /v1/* hit and bumps `merchant_usage_daily`
   for today.
2. `record_tx(merchant_id)` is called from the transactions endpoint
   after a successful send; bumps tx_count.
3. `enforce_quota(merchant_id, plan)` checks today's counters against
   the limits in PLAN_LIMITS and raises 429-equivalent when over.

Plans are static for V1 (constants in this file). When billing rolls
into production, move them into a `pricing_plans` table.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger("orgon.merchant_billing")


# Per-plan daily limits. -1 means unlimited.
PLAN_LIMITS: dict[str, dict[str, int]] = {
    "sandbox":   {"api_calls": 5_000,   "tx_count": 100,    "active_users": 50},
    "starter":   {"api_calls": 50_000,  "tx_count": 1_000,  "active_users": 500},
    "growth":    {"api_calls": 500_000, "tx_count": 10_000, "active_users": 10_000},
    "enterprise":{"api_calls": -1,      "tx_count": -1,     "active_users": -1},
}

# Plan with the most permissive limits to apply when merchant has no
# plan set yet. Errs on the side of not breaking existing flows.
_DEFAULT_PLAN = "sandbox"


def limits_for(plan: Optional[str]) -> dict[str, int]:
    return PLAN_LIMITS.get(plan or _DEFAULT_PLAN, PLAN_LIMITS[_DEFAULT_PLAN])


async def record_api_call(pool, merchant_id: str) -> None:
    """Bump api_calls counter for today. Best-effort: never raise."""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO merchant_usage_daily (merchant_id, day, api_calls)
                VALUES ($1, CURRENT_DATE, 1)
                ON CONFLICT (merchant_id, day) DO UPDATE SET
                    api_calls = merchant_usage_daily.api_calls + 1
                """,
                UUID(merchant_id),
            )
    except Exception as e:
        logger.debug("record_api_call failed (non-fatal): %s", e)


async def record_tx(pool, merchant_id: str) -> None:
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO merchant_usage_daily (merchant_id, day, tx_count)
                VALUES ($1, CURRENT_DATE, 1)
                ON CONFLICT (merchant_id, day) DO UPDATE SET
                    tx_count = merchant_usage_daily.tx_count + 1
                """,
                UUID(merchant_id),
            )
    except Exception as e:
        logger.debug("record_tx failed (non-fatal): %s", e)


async def today_counters(pool, merchant_id: str) -> dict[str, int]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT COALESCE(api_calls, 0)    AS api_calls,
                   COALESCE(tx_count, 0)     AS tx_count,
                   COALESCE(active_users, 0) AS active_users
              FROM merchant_usage_daily
             WHERE merchant_id = $1 AND day = CURRENT_DATE
            """,
            UUID(merchant_id),
        )
    if not row:
        return {"api_calls": 0, "tx_count": 0, "active_users": 0}
    return dict(row)


async def history(pool, *, merchant_id: str, days: int = 30) -> list[dict]:
    """Last N days of usage for the dashboard."""
    days = max(1, min(days, 90))
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT day, api_calls, tx_count, active_users
              FROM merchant_usage_daily
             WHERE merchant_id = $1
               AND day >= CURRENT_DATE - ($2::int - 1)
             ORDER BY day ASC
            """,
            UUID(merchant_id),
            days,
        )
    return [
        {
            "day": r["day"].isoformat(),
            "api_calls": r["api_calls"],
            "tx_count": r["tx_count"],
            "active_users": r["active_users"],
        }
        for r in rows
    ]


async def is_over_quota(
    pool, *, merchant_id: str, plan: Optional[str], metric: str,
) -> bool:
    """metric: 'api_calls' | 'tx_count' | 'active_users'."""
    lim = limits_for(plan).get(metric, -1)
    if lim < 0:
        return False
    counters = await today_counters(pool, merchant_id)
    return counters.get(metric, 0) >= lim
