from __future__ import annotations

from key_value._typing_compat import runtime_typing as _py38_typing
from typing import Any, SupportsFloat

from typing_extensions import override

from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.wrappers.base import BaseWrapper


class FallbackWrapper(BaseWrapper):
    """Wrapper that falls back to a secondary store when the primary store fails.

    This wrapper attempts operations on the primary store first. If the operation fails
    with one of the specified exceptions, it automatically falls back to the secondary store.
    This provides high availability and graceful degradation when the primary store is unavailable.

    Note: This wrapper only provides read fallback by default. Writes always go to the primary store.
    For write fallback, consider using write_to_fallback=True, but be aware of potential
    consistency issues.
    """

    def __init__(
        self,
        primary_key_value: AsyncKeyValue,
        fallback_key_value: AsyncKeyValue,
        fallback_on: _py38_typing.Tuple[_py38_typing.Type[Exception], ...] = (Exception,),
        write_to_fallback: bool = False,
    ) -> None:
        """Initialize the fallback wrapper.

        Args:
            primary_key_value: The primary store to use.
            fallback_key_value: The fallback store to use when primary fails.
            fallback_on: Tuple of exception types that trigger fallback. Defaults to (Exception,).
            write_to_fallback: If True, write operations also fall back to secondary store.
                               If False (default), write operations only go to primary.
        """
        self.primary_key_value: AsyncKeyValue = primary_key_value
        self.fallback_key_value: AsyncKeyValue = fallback_key_value
        self.fallback_on: _py38_typing.Tuple[_py38_typing.Type[Exception], ...] = fallback_on
        self.write_to_fallback: bool = write_to_fallback

        super().__init__()

    @override
    async def get(
        self, key: str, *, collection: _py38_typing.Union[str, None] = None
    ) -> _py38_typing.Union[_py38_typing.Dict[str, Any], None]:
        try:
            return await self.primary_key_value.get(key=key, collection=collection)
        except self.fallback_on:
            return await self.fallback_key_value.get(key=key, collection=collection)

    @override
    async def get_many(
        self, keys: _py38_typing.Sequence[str], *, collection: _py38_typing.Union[str, None] = None
    ) -> _py38_typing.List[_py38_typing.Union[_py38_typing.Dict[str, Any], None]]:
        try:
            return await self.primary_key_value.get_many(keys=keys, collection=collection)
        except self.fallback_on:
            return await self.fallback_key_value.get_many(keys=keys, collection=collection)

    @override
    async def ttl(
        self, key: str, *, collection: _py38_typing.Union[str, None] = None
    ) -> _py38_typing.Tuple[_py38_typing.Union[_py38_typing.Dict[str, Any], None], _py38_typing.Union[float, None]]:
        try:
            return await self.primary_key_value.ttl(key=key, collection=collection)
        except self.fallback_on:
            return await self.fallback_key_value.ttl(key=key, collection=collection)

    @override
    async def ttl_many(
        self, keys: _py38_typing.Sequence[str], *, collection: _py38_typing.Union[str, None] = None
    ) -> _py38_typing.List[_py38_typing.Tuple[_py38_typing.Union[_py38_typing.Dict[str, Any], None], _py38_typing.Union[float, None]]]:
        try:
            return await self.primary_key_value.ttl_many(keys=keys, collection=collection)
        except self.fallback_on:
            return await self.fallback_key_value.ttl_many(keys=keys, collection=collection)

    @override
    async def put(
        self,
        key: str,
        value: _py38_typing.Mapping[str, Any],
        *,
        collection: _py38_typing.Union[str, None] = None,
        ttl: _py38_typing.Union[SupportsFloat, None] = None,
    ) -> None:
        if self.write_to_fallback:
            try:
                return await self.primary_key_value.put(key=key, value=value, collection=collection, ttl=ttl)
            except self.fallback_on:
                return await self.fallback_key_value.put(key=key, value=value, collection=collection, ttl=ttl)
        else:
            return await self.primary_key_value.put(key=key, value=value, collection=collection, ttl=ttl)

    @override
    async def put_many(
        self,
        keys: _py38_typing.Sequence[str],
        values: _py38_typing.Sequence[_py38_typing.Mapping[str, Any]],
        *,
        collection: _py38_typing.Union[str, None] = None,
        ttl: _py38_typing.Union[SupportsFloat, None] = None,
    ) -> None:
        if self.write_to_fallback:
            try:
                return await self.primary_key_value.put_many(keys=keys, values=values, collection=collection, ttl=ttl)
            except self.fallback_on:
                return await self.fallback_key_value.put_many(keys=keys, values=values, collection=collection, ttl=ttl)
        else:
            return await self.primary_key_value.put_many(keys=keys, values=values, collection=collection, ttl=ttl)

    @override
    async def delete(self, key: str, *, collection: _py38_typing.Union[str, None] = None) -> bool:
        if self.write_to_fallback:
            try:
                return await self.primary_key_value.delete(key=key, collection=collection)
            except self.fallback_on:
                return await self.fallback_key_value.delete(key=key, collection=collection)
        else:
            return await self.primary_key_value.delete(key=key, collection=collection)

    @override
    async def delete_many(self, keys: _py38_typing.Sequence[str], *, collection: _py38_typing.Union[str, None] = None) -> int:
        if self.write_to_fallback:
            try:
                return await self.primary_key_value.delete_many(keys=keys, collection=collection)
            except self.fallback_on:
                return await self.fallback_key_value.delete_many(keys=keys, collection=collection)
        else:
            return await self.primary_key_value.delete_many(keys=keys, collection=collection)
