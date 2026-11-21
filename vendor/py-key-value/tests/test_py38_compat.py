"""Compatibility checks for data safety and runtime validation."""

from dataclasses import field, fields, replace
from pathlib import Path

import pytest
import keyring
from fakeredis.aioredis import FakeRedis

from key_value.aio._utils.compat import zip_strict
from key_value.aio._utils.dataclasses import keyword_only_dataclass
from key_value.aio.stores.filetree.store import _validate_resolved_path_within_directory
from key_value.aio.stores.keyring import KeyringStore
from key_value.aio.stores.memory import MemoryStore
from key_value.aio.stores.redis import RedisStore


def test_zip_strict_rejects_unequal_inputs():
    assert list(zip_strict([1, 2], ["a", "b"])) == [(1, "a"), (2, "b")]
    with pytest.raises(ValueError):
        list(zip_strict([1, 2], ["a"]))
    with pytest.raises(ValueError):
        list(zip_strict([1], ["a", "b"]))


def test_keyword_only_dataclass_preserves_defaults_and_required_fields():
    @keyword_only_dataclass
    class Entry:
        version: int = 1
        name: str
        values: list = field(default_factory=list)
        hidden: list = field(init=False, default_factory=list)

    entry = Entry(name="one")
    assert entry.version == 1
    assert [f.name for f in fields(entry)] == ["version", "name", "values", "hidden"]
    assert entry.values is not Entry(name="two").values
    assert entry.hidden is not Entry(name="two").hidden
    assert replace(entry, name="changed").name == "changed"
    with pytest.raises(TypeError):
        Entry("one")
    with pytest.raises(TypeError):
        Entry()


def test_path_containment_rejects_sibling_directory(tmp_path: Path):
    root = tmp_path / "root"
    assert _validate_resolved_path_within_directory(str(root / "child"), str(root))
    assert not _validate_resolved_path_within_directory(str(tmp_path / "root-other"), str(root))


@pytest.mark.asyncio
async def test_memory_store_rejects_invalid_key_types():
    store = MemoryStore()
    with pytest.raises(TypeError):
        await store.put(key=123, value={"value": "test"})


@pytest.mark.asyncio
async def test_redis_store_round_trip_with_async_client():
    client = FakeRedis(decode_responses=True)
    try:
        store = RedisStore(client=client)
        await store.put_many(["a", "b"], [{"value": 1}, {"value": 2}], collection="items")
        assert await store.get_many(["a", "b"], collection="items") == [{"value": 1}, {"value": 2}]
        assert set(await store.keys(collection="items")) == {"a", "b"}
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_keyring_store_round_trip(monkeypatch):
    entries = {}

    def get_password(service_name, username):
        return entries.get((service_name, username))

    def set_password(service_name, username, password):
        entries[(service_name, username)] = password

    def delete_password(service_name, username):
        del entries[(service_name, username)]

    monkeypatch.setattr(keyring, "get_password", get_password)
    monkeypatch.setattr(keyring, "set_password", set_password)
    monkeypatch.setattr(keyring, "delete_password", delete_password)
    store = KeyringStore(service_name="test")
    await store.put("token", {"value": "secret"})
    assert await store.get("token") == {"value": "secret"}
    assert await store.delete("token")
    assert await store.get("token") is None
