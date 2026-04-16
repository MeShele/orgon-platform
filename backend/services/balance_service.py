"""Balance aggregation service."""

import logging
from decimal import Decimal

from backend.safina.client import SafinaPayClient
from backend.database.db_postgres import AsyncDatabase
from backend.events.manager import get_event_manager, EventType

logger = logging.getLogger("orgon.services.balance")


class BalanceService:
    def __init__(self, client: SafinaPayClient, db: AsyncDatabase):
        self._client = client
        self._db = db

    async def get_summary(self) -> list[dict]:
        """Get aggregated token balances (user_tokens endpoint)."""
        try:
            tokens = await self._client.get_user_tokens()
            return [t.model_dump() for t in tokens]
        except Exception as e:
            logger.error("Failed to get balance summary: %s", e)
            # Fall back to cached
            return await self._get_cached_summary()

    async def _get_cached_summary(self) -> list[dict]:
        """Get summary from cached balances."""
        rows = await self._db.fetch(
            """SELECT token, SUM(CAST(REPLACE(value, ',', '.') AS NUMERIC)) as total_value
               FROM token_balances GROUP BY token"""
        )
        return [{"token": r["token"], "value": r["total_value"]} for r in rows]

    async def get_all_balances(self) -> list[dict]:
        """Get all token balances per wallet."""
        balances = await self._db.fetch(
            """SELECT tb.*, w.name as wallet_name, w.addr, w.info as wallet_info,
                      nc.network_name
               FROM token_balances tb
               LEFT JOIN wallets w ON tb.wallet_id = CAST(w.wallet_id AS TEXT)
               LEFT JOIN networks_cache nc ON tb.network = CAST(nc.network_id AS TEXT)
               ORDER BY tb.token"""
        )
        return balances

    async def get_dashboard_overview(self) -> dict:
        """Get aggregated data for dashboard overview."""
        # Wallet count
        wallet_count = await self._db.fetchrow(
            "SELECT COUNT(*) as cnt FROM wallets WHERE addr != ''"
        )

        # Token summary
        summary = await self.get_summary()
        total_tokens = len(summary)

        # Pending transactions
        pending_count = await self._db.fetchrow(
            "SELECT COUNT(*) as cnt FROM transactions WHERE status = 'pending'"
        )

        # Recent transactions
        recent_txs = await self._db.fetch(
            "SELECT * FROM transactions ORDER BY init_ts DESC LIMIT 10"
        )

        # Networks from cache
        networks = await self._db.fetch(
            "SELECT * FROM networks_cache WHERE status = 1"
        )

        # Last sync time
        last_sync = await self._db.fetchrow(
            "SELECT value FROM sync_state WHERE key = 'balances_synced'"
        )

        return {
            "wallet_count": wallet_count["cnt"] if wallet_count else 0,
            "total_tokens": total_tokens,
            "pending_tx_count": pending_count["cnt"] if pending_count else 0,
            "token_summary": summary,
            "recent_transactions": recent_txs,
            "networks": [dict(n) for n in networks],
            "last_sync": last_sync["value"] if last_sync else None,
        }

    async def record_balance_snapshot(self):
        """Record current balances for history chart."""
        summary = await self.get_summary()
        for item in summary:
            await self._db.execute(
                "INSERT INTO balance_history (token, total_value) VALUES ($1, $2)",
                (item["token"], str(item["value"])),
            )

    async def get_balance_history(self, days: int = 7) -> list[dict]:
        """Get balance history for charts."""
        return await self._db.fetch(
            """SELECT token, total_value, recorded_at
               FROM balance_history
               WHERE recorded_at >= NOW() - make_interval(days => $1)
               ORDER BY recorded_at""",
            (days,),
        )
