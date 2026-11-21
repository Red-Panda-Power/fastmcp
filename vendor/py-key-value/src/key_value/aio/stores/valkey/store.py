from __future__ import annotations

from key_value._typing_compat import runtime_typing as _py38_typing
import asyncio
import inspect
from typing import Any, overload

from typing_extensions import override

from key_value.aio._utils.compound import compound_key
from key_value.aio._utils.managed_entry import ManagedEntry
from key_value.aio.stores.base import BaseContextManagerStore, BaseStore

try:
    from glide import (
        ExpirySet,
        ExpiryType,
        GlideClient,
        GlideClientConfiguration,
        GlideClusterClient,
        GlideClusterClientConfiguration,
        NodeAddress,
        ServerCredentials,
    )
except ImportError:
    try:
        from redis.asyncio import Redis
    except ImportError as redis_error:
        msg = "ValkeyStore requires py-key-value-aio[valkey]"
        raise ImportError(msg) from redis_error

    _GLIDE_AVAILABLE = False
    ValkeyClient = Any
    # Keep postponed GLIDE annotations introspectable on Python 3.8. These
    # names are never used to construct a GLIDE client in the fallback path.
    ExpirySet = Any
    ExpiryType = Any
    GlideClient = Any
    GlideClientConfiguration = Any
    GlideClusterClient = Any
    GlideClusterClientConfiguration = Any
    NodeAddress = Any
    ServerCredentials = Any
else:
    _GLIDE_AVAILABLE = True
    ValkeyClient = _py38_typing.Union[GlideClient, GlideClusterClient]


DEFAULT_PAGE_SIZE = 10000
PAGE_LIMIT = 10000


# Private helper functions to encapsulate Valkey/Glide client creation with type ignore comments
# These are module-level functions (not methods) so they are not exported with the store class


def _create_valkey_client_config(
    *,
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    username: _py38_typing.Union[str, None] = None,
    password: _py38_typing.Union[str, None] = None,
) -> GlideClientConfiguration:
    """Create a Valkey client configuration."""
    if not _GLIDE_AVAILABLE:
        msg = "GLIDE configuration requires Python 3.9 or later; use host/port parameters or a redis.asyncio.Redis client on Python 3.8"
        raise ValueError(msg)

    addresses: _py38_typing.List[NodeAddress] = [NodeAddress(host=host, port=port)]
    credentials: _py38_typing.Union[ServerCredentials, None] = ServerCredentials(password=password, username=username) if password else None
    return GlideClientConfiguration(addresses=addresses, database_id=db, credentials=credentials)


@overload
async def _create_valkey_client(config: GlideClientConfiguration) -> GlideClient: ...


@overload
async def _create_valkey_client(config: GlideClusterClientConfiguration) -> GlideClusterClient: ...


async def _create_valkey_client(config: _py38_typing.Union[GlideClientConfiguration, GlideClusterClientConfiguration]) -> ValkeyClient:
    """Create a Valkey client from configuration."""
    if not _GLIDE_AVAILABLE:
        msg = "GLIDE configuration requires Python 3.9 or later"
        raise ValueError(msg)

    if isinstance(config, GlideClusterClientConfiguration):
        return await GlideClusterClient.create(config=config)

    return await GlideClient.create(config=config)


async def _valkey_mget(client: ValkeyClient, keys: _py38_typing.List[str]) -> _py38_typing.List[_py38_typing.Union[bytes, None]]:
    """Get multiple values from Valkey."""
    if _GLIDE_AVAILABLE:
        return await client.mget(keys=keys)  # pyright: ignore[reportArgumentType]
    # Redis Cluster rejects MGET when the keys map to different hash slots.
    # Individual GETs preserve ordering and work for both standalone and
    # clustered clients without requiring callers to add hash tags.
    responses = await asyncio.gather(*(client.get(name=key) for key in keys))  # pyright: ignore[reportUnknownMemberType]
    return list(responses)


async def _valkey_delete(client: ValkeyClient, keys: _py38_typing.List[str]) -> int:
    """Delete one or more keys from Valkey."""
    if _GLIDE_AVAILABLE:
        return await client.delete(keys=keys)  # pyright: ignore[reportArgumentType]
    # DEL has the same cluster-slot constraint as MGET. Delete one key at a
    # time in the fallback so multi-key operations remain usable with
    # RedisCluster injections.
    deleted = await asyncio.gather(*(client.delete(key) for key in keys))  # pyright: ignore[reportArgumentType,reportUnknownMemberType]
    return sum(deleted)


def _create_redis_valkey_client(
    *,
    host: str,
    port: int,
    db: int,
    username: _py38_typing.Union[str, None],
    password: _py38_typing.Union[str, None],
) -> Any:
    """Create the Redis-protocol fallback used when GLIDE is unavailable."""
    return Redis(host=host, port=port, db=db, username=username, password=password, decode_responses=False)


async def _close_redis_valkey_client(client: Any) -> None:
    """Close Redis clients across the redis-py versions supported by Python 3.8."""
    aclose = getattr(client, "aclose", None)
    close = aclose if aclose is not None else client.close
    result = close()
    if inspect.isawaitable(result):
        await result


class ValkeyStore(BaseContextManagerStore, BaseStore):
    """Valkey-based key-value store (Redis protocol compatible).

    Uses GLIDE when it is installed, including standalone and cluster deployments.
    Python 3.8 uses the compatible ``redis.asyncio`` protocol client instead;
    that fallback supports standalone host/port/auth connections and supplied
    Redis clients, but not GLIDE configuration or cluster client objects.
    """

    _connected_client: _py38_typing.Union[ValkeyClient, None]
    _client_config: _py38_typing.Union[GlideClientConfiguration, GlideClusterClientConfiguration, None]

    @overload
    def __init__(self, *, client: GlideClient, default_collection: _py38_typing.Union[str, None] = None) -> None: ...

    @overload
    def __init__(self, *, client: GlideClusterClient, default_collection: _py38_typing.Union[str, None] = None) -> None: ...

    @overload
    def __init__(
        self,
        *,
        config: _py38_typing.Union[GlideClientConfiguration, GlideClusterClientConfiguration],
        default_collection: _py38_typing.Union[str, None] = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        username: _py38_typing.Union[str, None] = None,
        password: _py38_typing.Union[str, None] = None,
        default_collection: _py38_typing.Union[str, None] = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        client: _py38_typing.Union[ValkeyClient, None] = None,
        config: _py38_typing.Union[GlideClientConfiguration, GlideClusterClientConfiguration, None] = None,
        default_collection: _py38_typing.Union[str, None] = None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        username: _py38_typing.Union[str, None] = None,
        password: _py38_typing.Union[str, None] = None,
    ) -> None:
        """Initialize the Valkey store.

        Args:
            client: An existing Valkey client to use (GlideClient or GlideClusterClient).
                If provided, the store will not manage the client's lifecycle (will not
                close it). The caller is responsible for managing the client's lifecycle.
            config: A GLIDE client configuration to connect lazily on first use.
                Pass ``GlideClientConfiguration`` for standalone Valkey or
                ``GlideClusterClientConfiguration`` for cluster-mode Valkey.
            default_collection: The default collection to use if no collection is provided.
            host: Valkey host. Defaults to localhost.
            port: Valkey port. Defaults to 6379.
            db: Valkey database number. Defaults to 0.
            username: Valkey username. Defaults to None.
            password: Valkey password. Defaults to None.

        Note:
            When using ``config`` or an existing ``client``, the host/port/db/
            username/password parameters are ignored.
        """
        client_provided = client is not None

        if client is not None and config is not None:
            msg = "client and config are mutually exclusive"
            raise ValueError(msg)

        if not _GLIDE_AVAILABLE and config is not None:
            msg = "GLIDE configuration requires Python 3.9 or later; use host/port parameters or a redis.asyncio.Redis client on Python 3.8"
            raise ValueError(msg)

        if client is not None:
            self._connected_client = client
            self._client_config = None
        elif config is not None:
            self._client_config = config
            self._connected_client = None
        elif _GLIDE_AVAILABLE:
            self._client_config = _create_valkey_client_config(host=host, port=port, db=db, username=username, password=password)
            self._connected_client = None
        else:
            self._client_config = None
            self._connected_client = _create_redis_valkey_client(
                host=host,
                port=port,
                db=db,
                username=username,
                password=password,
            )

        super().__init__(
            default_collection=default_collection,
            client_provided_by_user=client_provided,
            stable_api=True,
        )

    @override
    async def _setup(self) -> None:
        if self._connected_client is None:
            if self._client_config is None:
                # This should never happen, makes the type checker happy though
                msg = "Client configuration is not set"
                raise ValueError(msg)

            self._connected_client = await _create_valkey_client(self._client_config)

        # Register client cleanup if we own the client
        if not self._client_provided_by_user:
            if _GLIDE_AVAILABLE:
                self._exit_stack.push_async_callback(self._client.close)
            else:
                self._exit_stack.push_async_callback(_close_redis_valkey_client, self._client)

    @property
    def _client(self) -> ValkeyClient:
        if self._connected_client is None:
            # This should never happen, makes the type checker happy though
            msg = "Client is not connected"
            raise ValueError(msg)

        return self._connected_client

    @override
    async def _get_managed_entry(self, *, key: str, collection: str) -> _py38_typing.Union[ManagedEntry, None]:
        combo_key: str = compound_key(collection=collection, key=key)

        if _GLIDE_AVAILABLE:
            response: _py38_typing.Union[bytes, None] = await self._client.get(key=combo_key)
        else:
            response = await self._client.get(name=combo_key)  # pyright: ignore[reportUnknownMemberType]

        if not isinstance(response, bytes):
            return None

        decoded_response: str = response.decode("utf-8")

        return self._serialization_adapter.load_json(json_str=decoded_response)

    @override
    async def _get_managed_entries(
        self, *, collection: str, keys: _py38_typing.Sequence[str]
    ) -> _py38_typing.List[_py38_typing.Union[ManagedEntry, None]]:
        if not keys:
            return []

        combo_keys: _py38_typing.List[str] = [compound_key(collection=collection, key=key) for key in keys]

        responses: _py38_typing.List[_py38_typing.Union[bytes, None]] = await _valkey_mget(self._client, combo_keys)

        entries: _py38_typing.List[_py38_typing.Union[ManagedEntry, None]] = []
        for response in responses:
            if isinstance(response, bytes):
                decoded_response: str = response.decode("utf-8")
                entries.append(self._serialization_adapter.load_json(json_str=decoded_response))
            else:
                entries.append(None)

        return entries

    @override
    async def _put_managed_entry(
        self,
        *,
        key: str,
        collection: str,
        managed_entry: ManagedEntry,
    ) -> None:
        combo_key: str = compound_key(collection=collection, key=key)

        json_value: str = self._serialization_adapter.dump_json(entry=managed_entry, key=key, collection=collection)

        if _GLIDE_AVAILABLE:
            expiry: _py38_typing.Union[ExpirySet, None] = (
                ExpirySet(expiry_type=ExpiryType.SEC, value=int(managed_entry.ttl)) if managed_entry.ttl else None
            )
            _ = await self._client.set(key=combo_key, value=json_value, expiry=expiry)
        elif not managed_entry.ttl:
            _ = await self._client.set(name=combo_key, value=json_value)  # pyright: ignore[reportUnknownMemberType]
        else:
            _ = await self._client.set(name=combo_key, value=json_value, ex=int(managed_entry.ttl))  # pyright: ignore[reportUnknownMemberType]

    @override
    async def _delete_managed_entry(self, *, key: str, collection: str) -> bool:
        combo_key: str = compound_key(collection=collection, key=key)
        return await _valkey_delete(self._client, [combo_key]) != 0

    @override
    async def _delete_managed_entries(self, *, keys: _py38_typing.Sequence[str], collection: str) -> int:
        if not keys:
            return 0

        combo_keys: _py38_typing.List[str] = [compound_key(collection=collection, key=key) for key in keys]

        deleted_count: int = await _valkey_delete(self._client, combo_keys)

        return deleted_count
