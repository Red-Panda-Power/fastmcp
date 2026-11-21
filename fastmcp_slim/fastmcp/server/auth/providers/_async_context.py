"""Async-context compatibility helpers for authentication providers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypeVar

T = TypeVar("T")


@asynccontextmanager
async def async_nullcontext(value: T) -> AsyncGenerator[T, None]:
    """Yield a caller-owned value without taking ownership of its lifetime."""
    yield value
