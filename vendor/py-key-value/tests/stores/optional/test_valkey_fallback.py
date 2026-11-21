from __future__ import annotations

import subprocess
import sys
import typing
from typing import Any

import pytest
from redis.asyncio import RedisCluster

if sys.version_info < (3, 9):
    from key_value.aio.stores.valkey import ValkeyStore
    from key_value.aio.stores.valkey import store as valkey_store
else:
    ValkeyStore = Any
    valkey_store = None

PY38_FALLBACK_UNAVAILABLE = sys.version_info >= (3, 9) or (valkey_store is not None and valkey_store._GLIDE_AVAILABLE)


class CrossSlotRedisClient:
    """Minimal RedisCluster-like client that rejects cross-slot multi-key calls."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[dict[str, Any]] = []
        self.close_calls = 0

    async def get(self, *, name: str) -> bytes | None:
        value = self.values.get(name)
        return value.encode("utf-8") if value is not None else None

    async def set(self, *, name: str, value: str, ex: int | None = None) -> bool:
        self.set_calls.append({"name": name, "value": value, "ex": ex})
        self.values[name] = value
        return True

    async def delete(self, *keys: str) -> int:
        if len(keys) != 1:
            raise AssertionError("RedisCluster would reject a multi-slot DEL")
        return int(self.values.pop(keys[0], None) is not None)

    async def aclose(self) -> None:
        self.close_calls += 1


@pytest.mark.skipif(PY38_FALLBACK_UNAVAILABLE, reason="The test covers the Python 3.8 Redis-protocol fallback only")
async def test_redis_protocol_fallback_handles_cross_slot_multi_key_operations() -> None:
    client = CrossSlotRedisClient()
    store = ValkeyStore(client=client, default_collection="default")

    async with store:
        await store.put(key="one", value={"source": "fallback"})
        await store.put(key="two", value={"source": "fallback"}, ttl=60)
        assert await store.get(key="one") == {"source": "fallback"}
        assert await store.get_many(keys=["one", "two"]) == [{"source": "fallback"}, {"source": "fallback"}]
        assert await store.delete_many(keys=["one", "two"]) == 2
        assert await store.get(key="one") is None

    assert client.set_calls[0]["ex"] is None
    assert client.set_calls[1]["ex"] == 60
    assert client.close_calls == 0


@pytest.mark.skipif(PY38_FALLBACK_UNAVAILABLE, reason="The test covers the Python 3.8 Redis-protocol fallback only")
async def test_redis_protocol_fallback_closes_only_owned_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    client = CrossSlotRedisClient()
    monkeypatch.setattr(valkey_store, "_create_redis_valkey_client", lambda **_: client)

    async with ValkeyStore() as store:
        await store.put(key="key", value={"source": "owned"}, collection="test")

    assert client.close_calls == 1


@pytest.mark.skipif(PY38_FALLBACK_UNAVAILABLE, reason="The test covers the Python 3.8 Redis-protocol fallback only")
async def test_redis_protocol_fallback_accepts_redis_cluster_injection() -> None:
    cluster = RedisCluster(host="127.0.0.1", port=6379)
    store = ValkeyStore(client=cluster)

    assert store._client is cluster
    await cluster.aclose()


@pytest.mark.skipif(PY38_FALLBACK_UNAVAILABLE, reason="The test covers the Python 3.8 Redis-protocol fallback only")
def test_redis_protocol_fallback_preserves_runtime_type_hint_resolution() -> None:
    assert typing.get_type_hints(valkey_store._create_valkey_client)
    assert typing.get_type_hints(ValkeyStore.__init__)


@pytest.mark.skipif(PY38_FALLBACK_UNAVAILABLE, reason="The test covers the Python 3.8 Redis-protocol fallback only")
def test_redis_protocol_fallback_rejects_glide_configuration() -> None:
    with pytest.raises(ValueError, match="GLIDE configuration requires Python 3.9 or later"):
        ValkeyStore(config=object())


def test_valkey_store_import_reports_missing_optional_dependencies() -> None:
    code = """
import builtins

original_import = builtins.__import__

def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == 'glide' or name.startswith('glide.') or name == 'redis' or name.startswith('redis.'):
        raise ImportError('blocked optional dependency')
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = blocked_import
try:
    from key_value.aio.stores.valkey import ValkeyStore
except ImportError as error:
    assert str(error) == 'ValkeyStore requires py-key-value-aio[valkey]'
else:
    raise AssertionError('ValkeyStore import unexpectedly succeeded')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr


def test_valkey_import_fallback_is_limited_to_python_38() -> None:
    code = """
try:
    from key_value.aio.stores.valkey import store
except ImportError as error:
    print('error:' + str(error))
else:
    print('fallback:' + str(store._GLIDE_AVAILABLE))
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    if sys.version_info < (3, 9):
        assert result.stdout.strip() == "fallback:False"
    else:
        assert result.stdout.strip() == "error:ValkeyStore requires py-key-value-aio[valkey]"
