"""Tests for Redis cache helpers — uses the real Redis instance."""


async def test_cache_set_and_get():
    from memory.cache import cache_delete, cache_get, cache_set

    await cache_set("test:ping", {"value": 42}, ttl=60)
    result = await cache_get("test:ping")
    await cache_delete("test:ping")

    assert result == {"value": 42}


async def test_cache_get_returns_none_for_missing_key():
    from memory.cache import cache_get

    result = await cache_get("test:nonexistent_key_xyz")
    assert result is None


async def test_cache_set_overwrites_existing():
    from memory.cache import cache_delete, cache_get, cache_set

    await cache_set("test:overwrite", "first", ttl=60)
    await cache_set("test:overwrite", "second", ttl=60)
    result = await cache_get("test:overwrite")
    await cache_delete("test:overwrite")

    assert result == "second"


async def test_cache_delete_removes_key():
    from memory.cache import cache_delete, cache_get, cache_set

    await cache_set("test:delete_me", True, ttl=60)
    await cache_delete("test:delete_me")
    result = await cache_get("test:delete_me")

    assert result is None


async def test_cache_stores_list():
    from memory.cache import cache_delete, cache_get, cache_set

    await cache_set("test:list", ["AAPL", "NVDA", "TSLA"], ttl=60)
    result = await cache_get("test:list")
    await cache_delete("test:list")

    assert result == ["AAPL", "NVDA", "TSLA"]
