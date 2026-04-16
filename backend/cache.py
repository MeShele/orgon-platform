"""Simple in-memory async cache for frequently requested data."""
from datetime import datetime, timedelta
from functools import wraps

_cache: dict = {}


def cached(key: str, ttl_seconds: int = 60):
    """Decorator for async functions with TTL-based caching."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = datetime.utcnow()
            if key in _cache and _cache[key]["expires"] > now:
                return _cache[key]["data"]
            result = await func(*args, **kwargs)
            _cache[key] = {"data": result, "expires": now + timedelta(seconds=ttl_seconds)}
            return result
        return wrapper
    return decorator


def invalidate(key: str):
    """Remove a specific cache entry."""
    _cache.pop(key, None)


def invalidate_all():
    """Clear all cache entries."""
    _cache.clear()
