"""Python 3.8 compatibility checks for the client response cache."""

from __future__ import annotations

from mcp.client.caching import CacheKey

from fastmcp.client.caching import (
    CACHEABLE_RESULT_MODELS,
    KeyValueResponseCacheStore,
)


def test_cache_import_builds_allowlist_and_keeps_cache_keys_isolated() -> None:
    store = KeyValueResponseCacheStore()
    first = CacheKey("tools/list", "", "tenant-a")
    same = CacheKey("tools/list", "", "tenant-a")
    different_partition = CacheKey("tools/list", "", "tenant-b")
    different_params = CacheKey("tools/list", "different", "tenant-a")

    assert "ListToolsResult" in CACHEABLE_RESULT_MODELS
    assert store._string_key(first) == store._string_key(same)
    assert store._string_key(first) != store._string_key(different_partition)
    assert store._string_key(first) != store._string_key(different_params)
