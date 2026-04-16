"""Wallet business logic (Async PostgreSQL version)."""

import logging
from datetime import datetime, timezone

from backend.safina.client import SafinaPayClient
from backend.safina.models import CreateWalletRequest
from backend.database.db_postgres import AsyncDatabase

logger = logging.getLogger("orgon.services.wallet")


class WalletService:
    def __init__(self, client: SafinaPayClient, db: AsyncDatabase):
        self._client = client
        self._db = db

    async def list_wallets(self) -> list[dict]:
        """Get cached wallets, sync if empty."""
        wallets = await self._db.fetch(
            "SELECT * FROM wallets ORDER BY created_at DESC"
        )
        if not wallets:
            await self.sync_wallets()
            wallets = await self._db.fetch(
                "SELECT * FROM wallets ORDER BY created_at DESC"
            )
        return wallets

    async def get_wallet(self, name: str) -> dict | None:
        """Get wallet details from Safina + local DB."""
        local = await self._db.fetchrow("SELECT * FROM wallets WHERE name = $1", name)

        try:
            detail = await self._client.get_wallet(name)
        except Exception as e:
            logger.warning("Safina get_wallet(%s) failed: %s", name, e)
            detail = None

        if detail:
            result = detail.model_dump()
        elif local:
            # Fall back to local DB cache
            result = dict(local)
            result["wallet_name"] = local.get("name", name)
        else:
            return None

        if local:
            result["label"] = local.get("label")
            result["is_favorite"] = local.get("is_favorite", 0)
        return result

    async def get_wallet_tokens(self, wallet_name: str) -> list[dict]:
        """Get tokens for a wallet."""
        tokens = await self._client.get_wallet_tokens(wallet_name)
        return [t.model_dump() for t in tokens]

    async def create_wallet(self, request: CreateWalletRequest) -> str:
        """Create a new wallet via Safina API."""
        unid = await self._client.create_wallet(
            network=request.network,
            info=request.info,
            slist=request.slist,
        )

        # Cache locally
        await self._db.execute(
            """INSERT INTO wallets (name, network, info, my_unid, created_at)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (name) DO NOTHING""",
            unid, int(request.network), request.info, unid,
            datetime.now(timezone.utc)
        )

        logger.info("Wallet creation requested: UNID=%s, network=%s", unid, request.network)
        return unid

    async def sync_wallets(self):
        """Sync wallets from Safina API to local DB."""
        wallets = await self._client.get_wallets()
        now = datetime.now(timezone.utc)

        for w in wallets:
            await self._db.execute(
                """INSERT INTO wallets
                   (wallet_id, name, network, wallet_type, info, addr, addr_info,
                    my_unid, token_short_names, synced_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                   ON CONFLICT (name) DO UPDATE SET
                       wallet_id = EXCLUDED.wallet_id,
                       network = EXCLUDED.network,
                       wallet_type = EXCLUDED.wallet_type,
                       info = EXCLUDED.info,
                       addr = EXCLUDED.addr,
                       addr_info = EXCLUDED.addr_info,
                       my_unid = EXCLUDED.my_unid,
                       token_short_names = EXCLUDED.token_short_names,
                       synced_at = EXCLUDED.synced_at,
                       updated_at = EXCLUDED.updated_at
                   """,
                w.wallet_id, w.name, w.network, w.wallet_type, w.info,
                w.addr, w.addr_info, w.myUNID, w.tokenShortNames, now, now
            )

        await self._db.execute(
            """INSERT INTO sync_state (key, value, updated_at)
               VALUES ($1, $2, $3)
               ON CONFLICT (key) DO UPDATE SET
                   value = EXCLUDED.value,
                   updated_at = EXCLUDED.updated_at""",
            "wallets_synced", now.isoformat(), now
        )
        logger.info("Synced %d wallets from Safina", len(wallets))

    async def update_label(self, name: str, label: str) -> bool:
        """Update local wallet label."""
        result = await self._db.execute(
            "UPDATE wallets SET label = $1, updated_at = $2 WHERE name = $3",
            label, datetime.now(timezone.utc), name
        )
        return "UPDATE 1" in result

    async def toggle_favorite(self, name: str) -> bool:
        """Toggle wallet favorite status."""
        wallet = await self._db.fetchrow(
            "SELECT is_favorite FROM wallets WHERE name = $1", name
        )
        if not wallet:
            return False
        new_val = 0 if wallet["is_favorite"] else 1
        await self._db.execute(
            "UPDATE wallets SET is_favorite = $1, updated_at = $2 WHERE name = $3",
            new_val, datetime.now(timezone.utc), name
        )
        return True
