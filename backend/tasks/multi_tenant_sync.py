"""Per-tenant sync — fan out sync calls across every organization
with its own SAFINA_EC_PRIVATE_KEY.

Why this matters
----------------
Safina returns wallets / transactions / balances scoped to whoever
signed the request. The global sync run (legacy path, signed by the
env-var key) only ever sees its own customer's data — wallets that
ORGON tenants created under their own EC stay invisible to the global
sync, never get an addr update, never have their balances pulled.

Solution: iterate organizations that have a tenant key and run the
same sync operations under each.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Iterable
from uuid import UUID

from backend.database.db_postgres import AsyncDatabase
from backend.safina.factory import get_safina_client_for_org
from backend.services.wallet_service import WalletService
from backend.services.transaction_service import TransactionService
from backend.services.balance_service import BalanceService

logger = logging.getLogger("orgon.tasks.tenant_sync")


async def _list_tenants_with_keys(db: AsyncDatabase) -> list[UUID]:
    """Org UUIDs that have a safina_ec_private_key configured."""
    pool = db.pool
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id FROM organizations "
            "WHERE safina_ec_private_key IS NOT NULL "
            "  AND safina_ec_private_key != ''"
        )
    return [r["id"] for r in rows]


async def sync_wallets_all_tenants(db: AsyncDatabase) -> int:
    """Run sync_wallets under each tenant's EC, scoping new rows to the
    tenant via organization_id. Returns # of orgs processed."""
    org_ids = await _list_tenants_with_keys(db)
    count = 0
    for org_id in org_ids:
        try:
            client = await get_safina_client_for_org(db.pool, org_id)
            try:
                ws = WalletService(client, db)
                await ws.sync_wallets(organization_id=str(org_id))
                count += 1
                logger.debug("tenant wallet sync ok for org=%s", org_id)
            finally:
                await client.close()
        except Exception as exc:
            logger.warning("tenant wallet sync failed for org=%s: %s", org_id, exc)
    return count


async def sync_transactions_all_tenants(db: AsyncDatabase) -> int:
    org_ids = await _list_tenants_with_keys(db)
    count = 0
    for org_id in org_ids:
        try:
            client = await get_safina_client_for_org(db.pool, org_id)
            try:
                ts = TransactionService(client, db)
                await ts.sync_transactions()
                count += 1
            finally:
                await client.close()
        except Exception as exc:
            logger.warning("tenant tx sync failed for org=%s: %s", org_id, exc)
    return count


async def sync_balances_all_tenants(db: AsyncDatabase) -> int:
    org_ids = await _list_tenants_with_keys(db)
    count = 0
    for org_id in org_ids:
        try:
            client = await get_safina_client_for_org(db.pool, org_id)
            try:
                bs = BalanceService(client, db)
                await bs.sync_balances()
                count += 1
            finally:
                await client.close()
        except Exception as exc:
            logger.warning("tenant balance sync failed for org=%s: %s", org_id, exc)
    return count
