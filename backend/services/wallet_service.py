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

    async def count_wallets(
        self,
        network_id: int | None = None,
        org_ids: list | None = None,
    ) -> int:
        """Count wallets, optionally filtered by network and/or organization scope.

        `org_ids=None` means "no scoping" (super_admin / internal). An empty
        list means the caller has no organizations and the count is 0.
        """
        if org_ids is not None and not org_ids:
            return 0

        conditions: list[str] = []
        params: list = []
        idx = 1

        if network_id is not None:
            conditions.append(f"network_id = ${idx}")
            params.append(network_id)
            idx += 1

        if org_ids is not None:
            placeholders = ", ".join(f"${idx + i}" for i in range(len(org_ids)))
            conditions.append(f"organization_id IN ({placeholders})")
            params.extend(org_ids)
            idx += len(org_ids)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT COUNT(*) FROM wallets{where}"
        result = await self._db.fetchrow(query, params=tuple(params))
        return result["count"] if result else 0

    async def get_wallet_by_name(
        self,
        name: str,
        org_ids: list | None = None,
    ) -> dict | None:
        """Get wallet by name, optionally enforcing organization scope.

        If `org_ids` is provided and the wallet's organization_id is not in
        the list, returns None — same as if it didn't exist (avoids leaking
        existence to a tenant that shouldn't see it).
        """
        wallet = await self._db.fetchrow(
            "SELECT * FROM wallets WHERE name = $1",
            params=(name,)
        )
        if not wallet:
            return None
        if org_ids is not None:
            if not org_ids or wallet.get("organization_id") not in org_ids:
                return None
        return dict(wallet)

    @staticmethod
    def _ensure_addr_singular(result: dict) -> dict:
        """Safina `/wallet/:name` returns `addrs` (plural, multi-sig list).
        Frontend / DB schema use `addr` (singular). Map across so the
        single-wallet detail endpoint surfaces a usable address when the
        list endpoint (`/wallets`) returned empty.
        """
        addrs = result.get("addrs")
        existing = result.get("addr")
        if (not existing) and addrs:
            if isinstance(addrs, list) and addrs:
                result["addr"] = str(addrs[0])
            elif isinstance(addrs, str) and addrs:
                # Safina sometimes serialises addrs as comma-separated str
                first = addrs.split(",")[0].strip()
                result["addr"] = first
        return result

    async def get_wallet(self, name: str) -> dict | None:
        """Get wallet details from Safina + local DB.

        Accepts either the canonical Safina `name` (== `my_unid`) or
        the user-facing wallet name. Falls back to my_unid lookup if
        name lookup misses.
        """
        local = await self._db.fetchrow("SELECT * FROM wallets WHERE name = $1", params=(name,))
        if not local:
            local = await self._db.fetchrow(
                "SELECT * FROM wallets WHERE my_unid = $1", params=(name,),
            )

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
        return self._ensure_addr_singular(result)

    async def get_wallet_by_unid(self, unid: str) -> dict | None:
        """Lookup wallet by canonical Safina UNID.

        Tries Safina `/walletbyunid/:unid` first, falls back to local
        DB (`my_unid` then `name`). Used by `/api/wallets/by-unid/...`.
        """
        detail = None
        if self._client is not None:
            try:
                detail = await self._client.get_wallet_by_unid(unid)
            except Exception as e:
                logger.warning("Safina get_wallet_by_unid(%s) failed: %s", unid, e)

        local = await self._db.fetchrow(
            "SELECT * FROM wallets WHERE my_unid = $1", params=(unid,),
        )
        if not local:
            local = await self._db.fetchrow(
                "SELECT * FROM wallets WHERE name = $1", params=(unid,),
            )

        if detail:
            result = detail.model_dump()
        elif local:
            result = dict(local)
            result["wallet_name"] = local.get("name", unid)
        else:
            return None

        if local:
            result["label"] = local.get("label")
            result["is_favorite"] = local.get("is_favorite", 0)
        return self._ensure_addr_singular(result)

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
        request: CreateWalletRequest | None = None,
        organization_id: str | None = None,
    ) -> dict:
        """
        Create a new wallet via Safina API.

        Supports two call patterns:
        1. Partner API: create_wallet(name, network_id, wallet_type, label)
        2. Internal: create_wallet(request=CreateWalletRequest, organization_id=...)

        `organization_id` (UUID as str) attaches the new wallet to a
        tenant so /api/wallets list filtering finds it. Without it the
        new row lands at NULL and disappears from every tenant view.
        """
        if request is not None:
            return await self._create_wallet_internal(request, organization_id=organization_id)
        
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
    
    async def _create_wallet_internal(
        self,
        request: CreateWalletRequest,
        organization_id: str | None = None,
    ) -> str:
        """Create a new wallet via Safina API (internal format).

        organization_id (UUID as str) scopes the wallet to a tenant.
        If None, the row lands with NULL organization_id and is only
        visible to platform-level roles.
        """
        if self._client is None:
            raise RuntimeError("Safina client is not configured")
        unid = await self._client.create_wallet(
            network=request.network,
            info=request.info,
            slist=request.slist,
        )

        # Cache locally — include organization_id so tenant filter finds it.
        from uuid import UUID
        org_uuid = UUID(organization_id) if organization_id else None
        await self._db.execute(
            """INSERT INTO wallets (name, network, info, my_unid, organization_id, created_at)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT (name) DO NOTHING""",
            (unid, int(request.network), request.info, unid, org_uuid,
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
        # Stub client returns canned data without organization_id — syncing it
        # into shared `wallets` would pollute the table with rows invisible
        # under RLS. Demo data lives in migration 013 instead.
        if getattr(self._client, "is_stub", False):
            logger.debug("Skipping wallet sync: stub Safina client active")
            return
        wallets = await self._client.get_wallets()
        now = datetime.now(timezone.utc)

        for w in wallets:
            addr = w.addr or ""
            # List endpoint returns empty addr for fresh wallets — fetch
            # the detail endpoint (`/wallet/:name`) which returns `addrs`
            # (the multi-sig address list) and use the first entry.
            if not addr:
                try:
                    det = await self._client.get_wallet(w.name)
                    if det is not None:
                        det_dict = det.model_dump()
                        d_addrs = det_dict.get("addrs")
                        if isinstance(d_addrs, list) and d_addrs:
                            addr = str(d_addrs[0])
                        elif isinstance(d_addrs, str) and d_addrs:
                            addr = d_addrs.split(",")[0].strip()
                except Exception as e:
                    logger.debug("addr-detail fetch failed for %s: %s", w.name, e)

            await self._db.execute(
                """INSERT INTO wallets
                   (wallet_id, name, network, wallet_type, info, addr, addr_info,
                    my_unid, token_short_names, synced_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)

               ON CONFLICT (name) DO UPDATE SET
                   wallet_id = EXCLUDED.wallet_id, network = EXCLUDED.network, wallet_type = EXCLUDED.wallet_type, info = EXCLUDED.info, addr = EXCLUDED.addr, addr_info = EXCLUDED.addr_info, my_unid = EXCLUDED.my_unid, token_short_names = EXCLUDED.token_short_names, synced_at = EXCLUDED.synced_at, updated_at = EXCLUDED.updated_at""",
                (w.wallet_id, w.name, w.network, w.wallet_type, w.info,
                 addr, w.addr_info, w.myUNID, w.tokenShortNames, now, now),
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
