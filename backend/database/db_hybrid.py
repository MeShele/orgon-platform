"""Hybrid database wrapper: sync interface over async PostgreSQL.

This allows gradual migration from sync to async without rewriting all services at once.
"""

import asyncio
import logging
from typing import Any, Optional
from functools import wraps

from backend.database.db_postgres import AsyncDatabase

logger = logging.getLogger("orgon.database.hybrid")


def async_to_sync(async_func):
    """Decorator to run async function synchronously."""
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(async_func(*args, **kwargs))
    
    return wrapper


class HybridDatabase:
    """
    Sync wrapper over AsyncDatabase.
    
    Provides sync interface for legacy code while using async PostgreSQL underneath.
    
    Usage:
        db = HybridDatabase(async_db)
        rows = db.fetchall("SELECT * FROM wallets")  # sync call
    """
    
    def __init__(self, async_db: AsyncDatabase):
        self._async_db = async_db
        logger.info("HybridDatabase initialized (sync wrapper over async PostgreSQL)")
    
    @async_to_sync
    async def execute(self, sql: str, *params) -> str:
        """Execute SQL and return status (sync interface)."""
        # Convert ? placeholders to $1, $2, ...
        sql_pg, params_pg = self._convert_placeholders(sql, params)
        return await self._async_db.execute(sql_pg, *params_pg)
    
    @async_to_sync
    async def executemany(self, sql: str, params_list: list) -> None:
        """Execute SQL many times (sync interface)."""
        sql_pg, _ = self._convert_placeholders(sql, [])
        await self._async_db.executemany(sql_pg, params_list)
    
    @async_to_sync
    async def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        """Fetch all rows (sync interface)."""
        sql_pg, params_pg = self._convert_placeholders(sql, params)
        return await self._async_db.fetch(sql_pg, *params_pg)
    
    @async_to_sync
    async def fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Fetch one row (sync interface)."""
        sql_pg, params_pg = self._convert_placeholders(sql, params)
        return await self._async_db.fetchrow(sql_pg, *params_pg)
    
    @async_to_sync
    async def fetchval(self, sql: str, params: tuple = (), column: int = 0) -> Any:
        """Fetch single value (sync interface)."""
        sql_pg, params_pg = self._convert_placeholders(sql, params)
        return await self._async_db.fetchval(sql_pg, *params_pg, column=column)
    
    def get_connection(self):
        """Context manager not supported in hybrid mode."""
        raise NotImplementedError(
            "get_connection() not supported in HybridDatabase. "
            "Use execute/fetchall/fetchone instead."
        )
    
    def close(self):
        """Close underlying async database."""
        @async_to_sync
        async def _close():
            await self._async_db.close()
        _close()
    
    def _convert_placeholders(self, sql: str, params: tuple) -> tuple[str, list]:
        """
        Convert SQLite ? placeholders to PostgreSQL $1, $2, ...
        
        Returns:
            (converted_sql, params_list)
        """
        # Simple conversion: replace ? with $1, $2, $3, ...
        count = 0
        result = []
        for char in sql:
            if char == '?':
                count += 1
                result.append(f'${count}')
            else:
                result.append(char)
        
        return ''.join(result), list(params)


# Global instance
_hybrid_db: Optional[HybridDatabase] = None


def get_hybrid_db() -> HybridDatabase:
    """Get global hybrid database instance."""
    global _hybrid_db
    if _hybrid_db is None:
        from backend.database.db_postgres import get_db as get_async_db
        async_db = get_async_db()
        _hybrid_db = HybridDatabase(async_db)
    return _hybrid_db


async def init_hybrid_db(async_db: AsyncDatabase) -> HybridDatabase:
    """Initialize hybrid database."""
    global _hybrid_db
    _hybrid_db = HybridDatabase(async_db)
    return _hybrid_db
