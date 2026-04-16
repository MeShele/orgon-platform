# TODO: Add ON CONFLICT clauses to INSERT statements
"""Background sync service."""

import logging
from datetime import datetime, timezone

from backend.safina.client import SafinaPayClient
from backend.database.db_postgres import AsyncDatabase
from backend.events.manager import get_event_manager, EventType

logger = logging.getLogger("orgon.services.sync")


class SyncService:
    def __init__(self, client: SafinaPayClient, db: AsyncDatabase):
        self._client = client
        self._db = db

    async def sync_networks(self):
        """Sync network directory."""
        try:
            networks = await self._client.get_networks(1)
            now = datetime.now(timezone.utc)

            for n in networks:
                await self._db.execute(
                    """INSERT INTO networks_cache
                       (network_id, network_name, link, address_explorer,
                        tx_explorer, block_explorer, info, status, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               ON CONFLICT (network_id) DO UPDATE SET
                   network_name = EXCLUDED.network_name, link = EXCLUDED.link, address_explorer = EXCLUDED.address_explorer, tx_explorer = EXCLUDED.tx_explorer, block_explorer = EXCLUDED.block_explorer, info = EXCLUDED.info, status = EXCLUDED.status, updated_at = EXCLUDED.updated_at""",
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
            now = datetime.now(timezone.utc)

            for t in tokens:
                await self._db.execute(
                    """INSERT INTO tokens_info_cache
                       (token, commission, commission_min, commission_max, updated_at)
                       VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (token) DO UPDATE SET
                   commission = EXCLUDED.commission, commission_min = EXCLUDED.commission_min, commission_max = EXCLUDED.commission_max, updated_at = EXCLUDED.updated_at""",
                    (t.token, t.c, t.cMin, t.cMax, now),
                )

            logger.info("Synced %d token info entries", len(tokens))
        except Exception as e:
            logger.error("Failed to sync tokens info: %s", e)

    async def sync_balances(self):
        """Sync all token balances."""
        event_manager = get_event_manager()
        
        try:
            # Emit sync started event
            await event_manager.emit(EventType.SYNC_STARTED, {
                "type": "balances"
            })
            
            start_time = datetime.now(timezone.utc)
            tokens = await self._client.get_tokens()
            now = datetime.now(timezone.utc)

            # Clear old and insert fresh
            await self._db.execute("DELETE FROM token_balances")
            for t in tokens:
                await self._db.execute(
                    """INSERT INTO token_balances
                       (token_id, wallet_id, network, token, value, decimals, value_hex, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                    (str(t.id), str(t.wallet_id), str(t.network), t.token, str(t.value),
                     str(t.decimals), t.value_hex, now),
                )
                
                # Emit balance updated event for each token
                await event_manager.emit(EventType.BALANCE_UPDATED, {
                    "token": t.token,
                    "value": t.value,
                    "wallet_id": t.wallet_id,
                    "network": t.network
                })

            await self._db.execute(
                """INSERT INTO sync_state (key, value, updated_at) VALUES ($1, $2, $3)
                   ON CONFLICT (key) DO UPDATE SET
                   value = EXCLUDED.value, updated_at = EXCLUDED.updated_at""",
                ("balances_synced", now.isoformat(), now),
            )
            
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            logger.info("Synced %d token balances", len(tokens))
            
            # Emit sync completed event
            await event_manager.emit(EventType.SYNC_COMPLETED, {
                "type": "balances",
                "duration_ms": duration_ms,
                "items_synced": len(tokens)
            })
            
        except Exception as e:
            logger.error("Failed to sync balances: %s", e)
            await event_manager.emit(EventType.SYNC_FAILED, {
                "type": "balances",
                "error": str(e)
            })

    async def sync_all(self):
        """Run full sync cycle."""
        await self.sync_networks()
        await self.sync_tokens_info()
        await self.sync_balances()
