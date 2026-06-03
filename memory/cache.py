"""Redis cache helpers for hot data — prices, article counts, active signals."""

import json

import redis.asyncio as aioredis

from config.settings import get_settings

_settings = get_settings()


def _client() -> aioredis.Redis:
    return aioredis.from_url(_settings.redis_url, decode_responses=True)


async def cache_set(key: str, value: object, ttl: int = 300) -> None:
    """Store a JSON-serialisable value with a TTL (seconds)."""
    r = _client()
    await r.setex(key, ttl, json.dumps(value))
    await r.aclose()


async def cache_get(key: str) -> object:
    """Return the cached value, or None if missing / expired."""
    r = _client()
    data = await r.get(key)
    await r.aclose()
    return json.loads(data) if data else None


async def cache_delete(key: str) -> None:
    """Remove a key from the cache."""
    r = _client()
    await r.delete(key)
    await r.aclose()
