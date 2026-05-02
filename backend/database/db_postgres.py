"""PostgreSQL async connection manager for ORGON."""

import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

logger = logging.getLogger("orgon.database")


class AsyncDatabase:
    """Async PostgreSQL connection pool manager."""

    def __init__(self, connection_url: str, min_size: int = 0, max_size: int = 5):
        """
        Initialize async database connection pool.
        
        min_size=0 for Neon.tech serverless (lazy connection creation).
        This avoids cold start issues where database suspends and closes
        initial connections during pool creation.
        """
        self._connection_url = connection_url
        self._pool: Optional[asyncpg.Pool] = None
        self._min_size = min_size
        self._max_size = max_size
        logger.info("AsyncDatabase initialized (pool: %d-%d, lazy=%s)", min_size, max_size, min_size == 0)

    @property
    def pool(self) -> Optional[asyncpg.Pool]:
        """Public accessor for the underlying asyncpg pool.

        Some services (ComplianceService, etc.) prefer to construct
        their own pool-bound helpers instead of going through this
        wrapper for every query. Exposing the pool keeps that
        compositional pattern clean.
        """
        return self._pool

    async def connect(self):
        """Create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._connection_url,
                min_size=self._min_size,
                max_size=self._max_size,
                command_timeout=60,
                timeout=30,  # Connection timeout (for Neon.tech serverless)
            )
            logger.info("PostgreSQL connection pool created")

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if self._pool is None:
            await self.connect()
        
        async with self._pool.acquire() as conn:
            yield conn

    async def execute(self, sql: str, params=None) -> str:
        """Execute a SQL command and return status."""
        async with self.get_connection() as conn:
            if params:
                return await conn.execute(sql, *params)
            return await conn.execute(sql)

    async def executemany(self, sql: str, args_list: list) -> None:
        """Execute a SQL command many times."""
        async with self.get_connection() as conn:
            await conn.executemany(sql, args_list)

    async def fetch(self, sql: str, params=None) -> list[dict]:
        """Fetch all rows as list of dicts."""
        async with self.get_connection() as conn:
            if params:
                rows = await conn.fetch(sql, *params)
            else:
                rows = await conn.fetch(sql)
            return [dict(row) for row in rows]

    async def fetchrow(self, sql: str, params=None) -> Optional[dict]:
        """Fetch one row as dict."""
        async with self.get_connection() as conn:
            if params:
                row = await conn.fetchrow(sql, *params)
            else:
                row = await conn.fetchrow(sql)
            return dict(row) if row else None

    async def fetchval(self, sql: str, params=None, column: int = 0) -> Any:
        """Fetch a single value."""
        async with self.get_connection() as conn:
            if params:
                return await conn.fetchval(sql, *params, column=column)
            return await conn.fetchval(sql, column=column)


# Global instance
_db: Optional[AsyncDatabase] = None


def get_db() -> AsyncDatabase:
    """Get global database instance."""
    global _db
    if _db is None:
        from backend.config import get_config
        config = get_config()
        
        # Check if PostgreSQL URL is configured
        db_url = config.get("database", {}).get("postgresql_url")
        if not db_url:
            raise ValueError("PostgreSQL URL not configured in database.postgresql_url")
        
        _db = AsyncDatabase(db_url)
    return _db


async def init_db(connection_url: str) -> AsyncDatabase:
    """Initialize database with custom connection URL."""
    global _db
    _db = AsyncDatabase(connection_url)
    await _db.connect()
    return _db


async def close_db():
    """Close global database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
