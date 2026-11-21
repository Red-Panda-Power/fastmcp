from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from key_value.aio.stores.valkey import ValkeyStore
from key_value.aio.stores.valkey import store as valkey_store


@pytest.mark.skipif(valkey_store._GLIDE_AVAILABLE, reason="The test covers the Redis-protocol fallback only")
async def test_redis_protocol_fallback_preserves_valkey_store_operations() -> None:
    client = FakeRedis(decode_responses=False)
    store = ValkeyStore(client=client)

    async with store:
        await store.put(key="one", value={"source": "fallback"}, collection="test")
        await store.put(key="two", value={"source": "fallback"}, collection="test", ttl=60)
        assert await store.get(key="one", collection="test") == {"source": "fallback"}
        assert await store.get_many(keys=["one", "two"], collection="test") == [{"source": "fallback"}, {"source": "fallback"}]
        assert await store.delete_many(keys=["one", "two"], collection="test") == 2
        assert await store.get(key="one", collection="test") is None

    await client.aclose()
