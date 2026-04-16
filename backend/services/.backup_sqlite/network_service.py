"""Network and token reference data service with caching."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from backend.safina.client import SafinaPayClient
from backend.safina.models import Network, TokenInfo
from backend.database.db import Database

logger = logging.getLogger("orgon.services.network")

# Cache TTL: 1 hour
CACHE_TTL_SECONDS = 3600


class NetworkService:
    """
    Network and token reference data service.

    Features:
    - Caches networks and tokens_info with 1-hour TTL
    - Falls back to stale cache if Safina API unavailable
    - Background refresh support
    """

    def __init__(self, client: SafinaPayClient, db: Database):
        self._client = client
        self._db = db

    async def get_networks(self, status: int = 1, force_refresh: bool = False) -> list[Network]:
        """
        Get networks with caching.

        Args:
            status: 1 for active networks, 0 for disabled
            force_refresh: Skip cache and fetch from API

        Returns:
            List of Network objects
        """
        cache_key = f"networks_status_{status}"

        # Check cache freshness unless force refresh
        if not force_refresh:
            cached = self._get_cached_networks(status)
            if cached is not None:
                logger.debug("Networks cache hit (status=%d, count=%d)", status, len(cached))
                return cached

        # Cache miss or force refresh - fetch from API
        try:
            logger.info("Fetching networks from Safina API (status=%d)", status)
            networks = await self._client.get_networks(status)

            # Update cache
            await self._cache_networks(networks, status)

            # Update sync state
            self._db.execute(
                "INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES (?, ?, ?)",
                (cache_key, datetime.now(timezone.utc).isoformat(),
                 datetime.now(timezone.utc).isoformat()),
            )

            logger.info("Cached %d networks (status=%d)", len(networks), status)
            return networks

        except Exception as e:
            logger.error("Failed to fetch networks from API: %s", e)

            # Fall back to stale cache if available
            stale = self._get_cached_networks(status, allow_stale=True)
            if stale:
                logger.warning("Using stale networks cache (count=%d)", len(stale))
                return stale

            # No cache available, re-raise error
            raise

    def _get_cached_networks(
        self,
        status: int,
        allow_stale: bool = False
    ) -> Optional[list[Network]]:
        """
        Get networks from cache if fresh enough.

        Args:
            status: Network status filter
            allow_stale: Return cache even if expired (for fallback)

        Returns:
            Cached networks or None if cache miss/expired
        """
        # Check sync state for cache freshness
        cache_key = f"networks_status_{status}"
        state = self._db.fetchone(
            "SELECT value, updated_at FROM sync_state WHERE key = ?",
            (cache_key,)
        )

        if not state:
            return None

        # Check TTL
        if not allow_stale:
            updated_at = datetime.fromisoformat(state["updated_at"])
            age = datetime.now(timezone.utc) - updated_at.replace(tzinfo=timezone.utc)

            if age.total_seconds() > CACHE_TTL_SECONDS:
                logger.debug("Networks cache expired (age=%.1fs)", age.total_seconds())
                return None

        # Fetch from cache
        rows = self._db.fetchall(
            "SELECT * FROM networks_cache WHERE status = ? ORDER BY network_id",
            (status,)
        )

        if not rows:
            return None

        # Convert to Network objects
        networks = []
        for row in rows:
            networks.append(Network(
                network_id=row["network_id"],
                network_name=row["network_name"],
                link=row.get("link"),
                address_explorer=row.get("address_explorer"),
                tx_explorer=row.get("tx_explorer"),
                block_explorer=row.get("block_explorer"),
                info=row.get("info"),
                status=row["status"],
            ))

        return networks

    async def _cache_networks(self, networks: list[Network], status: int):
        """Store networks in cache."""
        # Clear old cache for this status
        self._db.execute("DELETE FROM networks_cache WHERE status = ?", (status,))

        # Insert new data
        now = datetime.now(timezone.utc).isoformat()
        for network in networks:
            self._db.execute(
                """INSERT OR REPLACE INTO networks_cache
                   (network_id, network_name, link, address_explorer, tx_explorer,
                    block_explorer, info, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    network.network_id,
                    network.network_name,
                    network.link,
                    network.address_explorer,
                    network.tx_explorer,
                    network.block_explorer,
                    network.info,
                    network.status,
                    now,
                ),
            )

    async def get_tokens_info(self, force_refresh: bool = False) -> list[TokenInfo]:
        """
        Get token commission info with caching.

        Args:
            force_refresh: Skip cache and fetch from API

        Returns:
            List of TokenInfo objects with commission data
        """
        cache_key = "tokens_info"

        # Check cache freshness unless force refresh
        if not force_refresh:
            cached = self._get_cached_tokens_info()
            if cached is not None:
                logger.debug("Tokens info cache hit (count=%d)", len(cached))
                return cached

        # Cache miss or force refresh - fetch from API
        try:
            logger.info("Fetching tokens info from Safina API")
            tokens_info = await self._client.get_tokens_info()

            # Update cache
            await self._cache_tokens_info(tokens_info)

            # Update sync state
            self._db.execute(
                "INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES (?, ?, ?)",
                (cache_key, datetime.now(timezone.utc).isoformat(),
                 datetime.now(timezone.utc).isoformat()),
            )

            logger.info("Cached %d tokens info", len(tokens_info))
            return tokens_info

        except Exception as e:
            logger.error("Failed to fetch tokens info from API: %s", e)

            # Fall back to stale cache if available
            stale = self._get_cached_tokens_info(allow_stale=True)
            if stale:
                logger.warning("Using stale tokens info cache (count=%d)", len(stale))
                return stale

            # No cache available, re-raise error
            raise

    def _get_cached_tokens_info(
        self,
        allow_stale: bool = False
    ) -> Optional[list[TokenInfo]]:
        """
        Get tokens info from cache if fresh enough.

        Args:
            allow_stale: Return cache even if expired (for fallback)

        Returns:
            Cached tokens info or None if cache miss/expired
        """
        # Check sync state for cache freshness
        cache_key = "tokens_info"
        state = self._db.fetchone(
            "SELECT value, updated_at FROM sync_state WHERE key = ?",
            (cache_key,)
        )

        if not state:
            return None

        # Check TTL
        if not allow_stale:
            updated_at = datetime.fromisoformat(state["updated_at"])
            age = datetime.now(timezone.utc) - updated_at.replace(tzinfo=timezone.utc)

            if age.total_seconds() > CACHE_TTL_SECONDS:
                logger.debug("Tokens info cache expired (age=%.1fs)", age.total_seconds())
                return None

        # Fetch from cache
        rows = self._db.fetchall("SELECT * FROM tokens_info_cache ORDER BY token")

        if not rows:
            return None

        # Convert to TokenInfo objects
        tokens_info = []
        for row in rows:
            tokens_info.append(TokenInfo(
                token=row["token"],
                c=row["commission"],
                cMin=row["commission_min"],
                cMax=row["commission_max"],
            ))

        return tokens_info

    async def _cache_tokens_info(self, tokens_info: list[TokenInfo]):
        """Store tokens info in cache."""
        # Clear old cache
        self._db.execute("DELETE FROM tokens_info_cache")

        # Insert new data
        now = datetime.now(timezone.utc).isoformat()
        for token_info in tokens_info:
            self._db.execute(
                """INSERT OR REPLACE INTO tokens_info_cache
                   (token, commission, commission_min, commission_max, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    token_info.token,
                    str(token_info.c),
                    str(token_info.cMin),
                    str(token_info.cMax),
                    now,
                ),
            )

    async def refresh_cache(self):
        """
        Background task to refresh cache periodically.

        This should be called from a scheduler (e.g., every hour).
        Refreshes both networks and tokens_info caches.
        """
        logger.info("Starting background cache refresh")

        try:
            # Refresh active networks
            await self.get_networks(status=1, force_refresh=True)

            # Refresh tokens info
            await self.get_tokens_info(force_refresh=True)

            logger.info("Background cache refresh completed")

        except Exception as e:
            logger.error("Background cache refresh failed: %s", e)
            # Don't raise - background refresh should not crash

    async def get_network_by_id(self, network_id: int) -> Optional[Network]:
        """
        Get a specific network by ID.

        Args:
            network_id: Network ID to lookup

        Returns:
            Network object or None if not found
        """
        # Get all active networks (from cache)
        networks = await self.get_networks(status=1)

        # Find by ID
        for network in networks:
            if network.network_id == network_id:
                return network

        return None

    async def get_token_info(self, token: str) -> Optional[TokenInfo]:
        """
        Get commission info for a specific token.

        Args:
            token: Token identifier (format: "network:::TOKEN")

        Returns:
            TokenInfo object or None if not found
        """
        # Get all tokens info (from cache)
        tokens_info = await self.get_tokens_info()

        # Find by token
        for token_info in tokens_info:
            if token_info.token == token:
                return token_info

        return None

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics for monitoring.

        Returns:
            Dict with cache age and sizes
        """
        stats = {}

        # Networks cache
        networks_state = self._db.fetchone(
            "SELECT updated_at FROM sync_state WHERE key = ?",
            ("networks_status_1",)
        )
        if networks_state:
            updated_at = datetime.fromisoformat(networks_state["updated_at"])
            age = datetime.now(timezone.utc) - updated_at.replace(tzinfo=timezone.utc)
            stats["networks_age_seconds"] = int(age.total_seconds())
            stats["networks_fresh"] = age.total_seconds() < CACHE_TTL_SECONDS

        networks_count = self._db.fetchone("SELECT COUNT(*) as cnt FROM networks_cache")
        stats["networks_count"] = networks_count["cnt"] if networks_count else 0

        # Tokens info cache
        tokens_state = self._db.fetchone(
            "SELECT updated_at FROM sync_state WHERE key = ?",
            ("tokens_info",)
        )
        if tokens_state:
            updated_at = datetime.fromisoformat(tokens_state["updated_at"])
            age = datetime.now(timezone.utc) - updated_at.replace(tzinfo=timezone.utc)
            stats["tokens_info_age_seconds"] = int(age.total_seconds())
            stats["tokens_info_fresh"] = age.total_seconds() < CACHE_TTL_SECONDS

        tokens_count = self._db.fetchone("SELECT COUNT(*) as cnt FROM tokens_info_cache")
        stats["tokens_info_count"] = tokens_count["cnt"] if tokens_count else 0

        return stats
