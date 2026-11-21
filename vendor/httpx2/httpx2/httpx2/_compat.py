"""Small context manager backports for Python 3.8 and 3.9."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Protocol, TypeVar

T = TypeVar("T")


class AsyncClosable(Protocol):
    async def aclose(self) -> None: ...


Closable = TypeVar("Closable", bound=AsyncClosable)


@asynccontextmanager
async def aclosing(thing: Closable) -> AsyncIterator[Closable]:
    try:
        yield thing
    finally:
        await thing.aclose()


@asynccontextmanager
async def async_nullcontext(thing: T) -> AsyncIterator[T]:
    yield thing
