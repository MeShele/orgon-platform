"""Background sync service."""

import logging
from datetime import datetime, timezone

from backend.safina.client import SafinaPayClient
from backend.database.db import Database

logger = logging.getLogger("orgon.services.sync")


class SyncService:
    def __init__(self, client: SafinaPayClient, db: Database):
        self._client = client
        self._db = db

    async def sync_networks(self):
        """Sync network directory."""
        try:
            networks = await self._client.get_networks(1)
            now = datetime.now(timezone.utc).isoformat()

            for n in networks:
                self._db.execute(
                    """INSERT OR REPLACE INTO networks_cache
                       (network_id, network_name, link, address_explorer,
                        tx_explorer, block_explorer, info, status, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (n.network_id, n.network_name, n.link, n.address_explorer,
                     n.tx_explorer, n.block_explorer, n.info, n.status, now),
                )

            logger.info("Synced %d networks", len(networks))
        except Exception as e:
            logger.error("Failed to sync networks: %s", e)

    async def sync_tokens_info(self):
        """Sync token commission directory."""
        try:
            tokens = await self._client.get_tokens_info()
            now = datetime.now(timezone.utc).isoformat()

            for t in tokens:
                self._db.execute(
                    """INSERT OR REPLACE INTO tokens_info_cache
                       (token, commission, commission_min, commission_max, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (t.token, t.c, t.cMin, t.cMax, now),
                )

            logger.info("Synced %d token info entries", len(tokens))
        except Exception as e:
            logger.error("Failed to sync tokens info: %s", e)

    async def sync_balances(self):
        """Sync all token balances."""
        try:
            tokens = await self._client.get_tokens()
            now = datetime.now(timezone.utc).isoformat()

            # Clear old and insert fresh
            self._db.execute("DELETE FROM token_balances")
            for t in tokens:
                self._db.execute(
                    """INSERT INTO token_balances
                       (token_id, wallet_id, network, token, value, decimals, value_hex, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (t.id, t.wallet_id, t.network, t.token, t.value,
                     t.decimals, t.value_hex, now),
                )

            self._db.execute(
                "INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES (?, ?, ?)",
                ("balances_synced", now, now),
            )
            logger.info("Synced %d token balances", len(tokens))
        except Exception as e:
            logger.error("Failed to sync balances: %s", e)

    async def sync_all(self):
        """Run full sync cycle."""
        await self.sync_networks()
        await self.sync_tokens_info()
        await self.sync_balances()
