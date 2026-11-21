from __future__ import annotations

from key_value._typing_compat import runtime_typing as _py38_typing
from typing_extensions import override

from key_value.aio._utils.managed_entry import ManagedEntry
from key_value.aio.stores.base import BaseStore


class NullStore(BaseStore):
    """Null object pattern store that accepts all operations but stores nothing."""

    @override
    async def _get_managed_entry(self, *, key: str, collection: str) -> _py38_typing.Union[ManagedEntry, None]:
        return None

    @override
    async def _put_managed_entry(
        self,
        *,
        key: str,
        collection: str,
        managed_entry: ManagedEntry,
    ) -> None:
        pass

    @override
    async def _delete_managed_entry(self, *, key: str, collection: str) -> bool:
        return False
