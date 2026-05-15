"""Monthly invoice generation + lookup.

Policy V1:
  base monthly fee + overage on api_calls / tx_count.
  Prices are USD, defined in PLAN_PRICING constants.

`generate_invoices_for_month(period_start)` is called by the
scheduler on the 1st of every month (UTC). It iterates every
merchant that had any usage in the previous month, sums up
merchant_usage_daily rows in the period, computes line items, and
INSERTs an invoice row. Idempotent on (merchant_id, billing_period).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

logger = logging.getLogger("orgon.invoice")


# Monthly base + per-unit overage (USD). -1 means unlimited (no
# overage charge once the merchant is on enterprise).
PLAN_PRICING: dict[str, dict[str, Decimal]] = {
    "sandbox":   {"base": Decimal("0.00"),   "api_overage_per_k": Decimal("0.00"),  "tx_overage": Decimal("0.00"),  "api_quota": Decimal("5000"),    "tx_quota": Decimal("100")},
    "starter":   {"base": Decimal("99.00"),  "api_overage_per_k": Decimal("0.10"),  "tx_overage": Decimal("0.05"),  "api_quota": Decimal("50000"),   "tx_quota": Decimal("1000")},
    "growth":    {"base": Decimal("499.00"), "api_overage_per_k": Decimal("0.05"),  "tx_overage": Decimal("0.02"),  "api_quota": Decimal("500000"),  "tx_quota": Decimal("10000")},
    "enterprise":{"base": Decimal("2499.00"),"api_overage_per_k": Decimal("0.00"),  "tx_overage": Decimal("0.00"),  "api_quota": Decimal("-1"),      "tx_quota": Decimal("-1")},
}


def previous_month_period(today: date) -> date:
    """First day of the previous calendar month."""
    y, m = today.year, today.month - 1
    if m == 0:
        y, m = y - 1, 12
    return date(y, m, 1)


def _next_month(d: date) -> date:
    y, m = d.year, d.month + 1
    if m == 13:
        y, m = y + 1, 1
    return date(y, m, 1)


async def generate_invoices_for_month(pool, *, period_start: date) -> int:
    """Generate invoices for every merchant that had usage in
    [period_start, next_month(period_start)). Returns count created.

    Re-running for the same period is safe — UNIQUE (merchant_id,
    billing_period) means second insert is a no-op.
    """
    period_end = _next_month(period_start)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.merchant_id::text AS merchant_id,
                   COALESCE(SUM(u.api_calls), 0)::int  AS api_calls,
                   COALESCE(SUM(u.tx_count), 0)::int   AS tx_count,
                   COALESCE(MAX(u.active_users), 0)::int AS active_users_peak,
                   o.pricing_plan,
                   o.name AS merchant_name
              FROM merchant_usage_daily u
              JOIN organizations o ON o.id = u.merchant_id
             WHERE u.day >= $1 AND u.day < $2
             GROUP BY u.merchant_id, o.pricing_plan, o.name
            """,
            period_start,
            period_end,
        )

    created = 0
    for r in rows:
        try:
            inv = _build_invoice(
                plan=r["pricing_plan"] or "sandbox",
                api_calls=r["api_calls"],
                tx_count=r["tx_count"],
            )
            async with pool.acquire() as conn:
                result = await conn.execute(
                    """
                    INSERT INTO invoices
                        (merchant_id, billing_period, plan, currency,
                         amount_total, items, api_calls_total, tx_count_total)
                    VALUES ($1, $2, $3, 'USD', $4, $5::jsonb, $6, $7)
                    ON CONFLICT (merchant_id, billing_period) DO NOTHING
                    """,
                    UUID(r["merchant_id"]),
                    period_start,
                    r["pricing_plan"] or "sandbox",
                    inv["amount_total"],
                    json.dumps(inv["items"]),
                    r["api_calls"],
                    r["tx_count"],
                )
            if result.endswith(" 1"):
                created += 1
                logger.info(
                    "invoice generated merchant=%s (%s) period=%s amount=$%s",
                    r["merchant_id"], r["merchant_name"], period_start, inv["amount_total"],
                )
        except Exception as e:
            logger.error("invoice gen failed merchant=%s: %s", r["merchant_id"], e)
    return created


def _build_invoice(*, plan: str, api_calls: int, tx_count: int) -> dict:
    """Pure computation: plan + usage → line items + total."""
    pricing = PLAN_PRICING.get(plan, PLAN_PRICING["sandbox"])
    items: list[dict] = []

    # Base fee.
    if pricing["base"] > 0:
        items.append({"label": f"{plan.title()} plan", "amount": float(pricing["base"])})

    # API overage — charged per 1,000 calls.
    api_quota = pricing["api_quota"]
    if api_quota >= 0:
        api_overage = max(0, api_calls - int(api_quota))
        if api_overage > 0 and pricing["api_overage_per_k"] > 0:
            overage_k = Decimal(api_overage) / Decimal(1000)
            amt = (overage_k * pricing["api_overage_per_k"]).quantize(Decimal("0.01"))
            items.append({
                "label": f"API calls overage (over {int(api_quota):,}/day daily limit summed)",
                "qty": api_overage,
                "unit_per_1000": float(pricing["api_overage_per_k"]),
                "amount": float(amt),
            })

    # Tx overage — charged per tx.
    tx_quota = pricing["tx_quota"]
    if tx_quota >= 0:
        tx_overage = max(0, tx_count - int(tx_quota))
        if tx_overage > 0 and pricing["tx_overage"] > 0:
            amt = (Decimal(tx_overage) * pricing["tx_overage"]).quantize(Decimal("0.01"))
            items.append({
                "label": "Transaction overage",
                "qty": tx_overage,
                "unit": float(pricing["tx_overage"]),
                "amount": float(amt),
            })

    total = sum(Decimal(str(i["amount"])) for i in items)
    return {"amount_total": total, "items": items}


async def list_invoices(
    pool, *, merchant_id: str, limit: int = 24
) -> list[dict]:
    """Most recent N invoices for a merchant. Default 2 years."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, billing_period, plan, currency,
                   amount_total, items, api_calls_total, tx_count_total,
                   status, issued_at, paid_at
              FROM invoices
             WHERE merchant_id = $1
             ORDER BY billing_period DESC
             LIMIT $2
            """,
            UUID(merchant_id),
            limit,
        )
    out: list[dict] = []
    for r in rows:
        items = r["items"]
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except Exception:
                items = []
        out.append({
            "id": r["id"],
            "billing_period": r["billing_period"].isoformat(),
            "plan": r["plan"],
            "currency": r["currency"],
            "amount_total": str(r["amount_total"]),
            "items": items,
            "api_calls_total": r["api_calls_total"],
            "tx_count_total": r["tx_count_total"],
            "status": r["status"],
            "issued_at": r["issued_at"].isoformat() if r.get("issued_at") else None,
            "paid_at": r["paid_at"].isoformat() if r.get("paid_at") else None,
        })
    return out


async def mark_paid(pool, *, invoice_id: str) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE invoices
               SET status = 'paid', paid_at = now()
             WHERE id = $1 AND status = 'open'
            RETURNING id::text, merchant_id::text AS merchant_id, status, paid_at
            """,
            UUID(invoice_id),
        )
    if not row:
        return None
    return dict(row)
