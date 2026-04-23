# TODO: Add ON CONFLICT clauses to INSERT statements
"""Wallet business logic."""

import logging
from datetime import datetime, timezone

from backend.safina.client import SafinaPayClient
from backend.safina.models import CreateWalletRequest
from backend.database.db_postgres import AsyncDatabase
from backend.events.manager import get_event_manager, EventType

logger = logging.getLogger("orgon.services.wallet")


class WalletService:
    def __init__(self, client: SafinaPayClient, db: AsyncDatabase):
        self._client = client
        self._db = db

    async def list_wallets(
        self,
        network_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
        org_ids: list | None = None
    ) -> list[dict]:
        """
        Get cached wallets with optional filtering and pagination.

        Args:
            network_id: Optional network filter
            limit: Maximum number of wallets to return
            offset: Offset for pagination

        Returns:
            List of wallet dictionaries
        """
        # If no Safina client, only return cached data (no auto-sync)
        # Build query with optional filters
        conditions = []
        params = []
        idx = 1
        
        if network_id is not None:
            conditions.append(f"network_id = ${idx}")
            params.append(network_id)
            idx += 1
        
        if org_ids is not None:  # None = no filter (super_admin)
            if not org_ids:
                return []  # User has no orgs - empty result
            placeholders = ", ".join(f"${idx + i}" for i in range(len(org_ids)))
            conditions.append(f"organization_id IN ({placeholders})")
            params.extend(org_ids)
            idx += len(org_ids)
        
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM wallets{where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        params.extend([limit, offset])
        
        wallets = await self._db.fetch(query, params=tuple(params))
        
        # If no wallets and no offset, try syncing (only if client available)
        if not wallets and offset == 0 and self._client is not None:
            await self.sync_wallets()
            wallets = await self._db.fetch(query, params=tuple(params))
        
        return wallets

    async def count_wallets(self, network_id: int | None = None) -> int:
        """
        Count total wallets with optional network filter.
        
        Args:
            network_id: Optional network filter
            
        Returns:
            Total count of wallets
        """
        if network_id is not None:
            query = "SELECT COUNT(*) FROM wallets WHERE network_id = $1"
            result = await self._db.fetchrow(query, params=(network_id,))
        else:
            query = "SELECT COUNT(*) FROM wallets"
            result = await self._db.fetchrow(query)
        
        return result["count"] if result else 0
    
    async def get_wallet_by_name(self, name: str) -> dict | None:
        """
        Get wallet from local database by name.
        
        Args:
            name: Wallet name
            
        Returns:
            Wallet dictionary or None if not found
        """
        wallet = await self._db.fetchrow(
            "SELECT * FROM wallets WHERE name = $1",
            params=(name,)
        )
        return dict(wallet) if wallet else None

    async def get_wallet(self, name: str) -> dict | None:
        """Get wallet details from Safina + local DB."""
        local = await self._db.fetchrow("SELECT * FROM wallets WHERE name = $1", params=(name,))

        detail = None
        if self._client is not None:
            try:
                detail = await self._client.get_wallet(name)
            except Exception as e:
                logger.warning("Safina get_wallet(%s) failed: %s", name, e)

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
        if self._client is None:
            return []
        tokens = await self._client.get_wallet_tokens(wallet_name)
        return [t.model_dump() for t in tokens]

    async def create_wallet(
        self, 
        name: str | None = None,
        network_id: int | None = None,
        wallet_type: int = 1,
        label: str | None = None,
        request: CreateWalletRequest | None = None
    ) -> dict:
        """
        Create a new wallet via Safina API.
        
        Supports two call patterns:
        1. Partner API: create_wallet(name, network_id, wallet_type, label)
        2. Internal: create_wallet(request=CreateWalletRequest)
        
        Args:
            name: Wallet name (Partner API)
            network_id: Network ID (Partner API)
            wallet_type: Wallet type, default 1=multisig (Partner API)
            label: Optional label (Partner API)
            request: CreateWalletRequest object (Internal API)
            
        Returns:
            Wallet dictionary with created wallet details
        """
        # Handle internal API call (with CreateWalletRequest)
        if request is not None:
            return await self._create_wallet_internal(request)
        
        # Handle Partner API call (with individual params)
        if name is None or network_id is None:
            raise ValueError("name and network_id are required for Partner API wallet creation")
        if self._client is None:
            raise RuntimeError("Safina client is not configured")

        # Create wallet via Safina API (Partner API format)
        # Note: Safina API uses different format - need to build CreateWalletRequest
        # For now, create a simple wallet with defaults
        wallet_request = CreateWalletRequest(
            network=str(network_id),
            info=label or f"Wallet {name}",
            slist=None  # Will be populated later via Safina dashboard
        )
        
        unid = await self._client.create_wallet(
            network=wallet_request.network,
            info=wallet_request.info,
            slist=wallet_request.slist,
        )
        
        # Cache locally
        now = datetime.now(timezone.utc)
        await self._db.execute(
            """INSERT INTO wallets (name, network, info, my_unid, created_at, synced_at)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT (name) DO UPDATE SET
               network = EXCLUDED.network, info = EXCLUDED.info, synced_at = EXCLUDED.synced_at""",
            (unid, network_id, wallet_request.info, unid, now, now),
        )
        
        logger.info("Partner API wallet created: name=%s, network=%d", unid, network_id)
        
        # Emit wallet created event
        event_manager = get_event_manager()
        await event_manager.emit(EventType.WALLET_CREATED, {
            "name": unid,
            "network": network_id,
            "info": wallet_request.info
        })
        
        # Return wallet details
        return {
            "name": unid,
            "network": network_id,
            "wallet_type": wallet_type,
            "addr": "",  # Will be populated after sync
            "label": label,
            "is_favorite": 0,
            "created_at": now.isoformat(),
            "synced_at": now.isoformat()
        }
    
    async def _create_wallet_internal(self, request: CreateWalletRequest) -> str:
        """Create a new wallet via Safina API (internal format)."""
        if self._client is None:
            raise RuntimeError("Safina client is not configured")
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
            (unid, int(request.network), request.info, unid,
             datetime.now(timezone.utc)),
        )

        logger.info("Wallet creation requested: UNID=%s, network=%s", unid, request.network)
        
        # Emit wallet created event
        event_manager = get_event_manager()
        await event_manager.emit(EventType.WALLET_CREATED, {
            "name": unid,
            "network": request.network,
            "info": request.info
        })
        
        return unid

    async def sync_wallets(self):
        """Sync wallets from Safina API to local DB."""
        if self._client is None:
            logger.debug("Skipping wallet sync: Safina client not configured")
            return
        wallets = await self._client.get_wallets()
        now = datetime.now(timezone.utc)

        for w in wallets:
            await self._db.execute(
                """INSERT INTO wallets
                   (wallet_id, name, network, wallet_type, info, addr, addr_info,
                    my_unid, token_short_names, synced_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                   
               ON CONFLICT (name) DO UPDATE SET
                   wallet_id = EXCLUDED.wallet_id, network = EXCLUDED.network, wallet_type = EXCLUDED.wallet_type, info = EXCLUDED.info, addr = EXCLUDED.addr, addr_info = EXCLUDED.addr_info, my_unid = EXCLUDED.my_unid, token_short_names = EXCLUDED.token_short_names, synced_at = EXCLUDED.synced_at, updated_at = EXCLUDED.updated_at""",
                (w.wallet_id, w.name, w.network, w.wallet_type, w.info,
                 w.addr, w.addr_info, w.myUNID, w.tokenShortNames, now, now),
            )

        await self._db.execute(
            """INSERT INTO sync_state (key, value, updated_at) VALUES ($1, $2, $3)
               ON CONFLICT (key) DO UPDATE SET
               value = EXCLUDED.value, updated_at = EXCLUDED.updated_at""",
            ("wallets_synced", now.isoformat(), now),
        )
        logger.info("Synced %d wallets from Safina", len(wallets))

    async def update_label(self, name: str, label: str) -> bool:
        """Update local wallet label."""
        cursor = await self._db.execute(
            "UPDATE wallets SET label = $1, updated_at = $2 WHERE name = $3",
            (label, datetime.now(timezone.utc), name),
        )
        return cursor.rowcount > 0

    async def toggle_favorite(self, name: str) -> bool:
        """Toggle wallet favorite status."""
        wallet = await self._db.fetchrow("SELECT is_favorite FROM wallets WHERE name = $1", params=(name,))
        if not wallet:
            return False
        new_val = 0 if wallet["is_favorite"] else 1
        await self._db.execute(
            "UPDATE wallets SET is_favorite = $1, updated_at = $2 WHERE name = $3",
            (new_val, datetime.now(timezone.utc), name),
        )
        return True
