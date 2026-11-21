"""Compatibility helpers for standard-library features added after Python 3.8."""

from __future__ import annotations

from itertools import zip_longest
from typing import TypeVar, cast

from key_value._typing_compat import runtime_typing as _py38_typing

T = TypeVar("T")
U = TypeVar("U")


def zip_strict(first: _py38_typing.Iterable[T], second: _py38_typing.Iterable[U]) -> _py38_typing.Iterator[_py38_typing.Tuple[T, U]]:
    """Zip two iterables and reject unequal lengths."""
    missing = object()
    for left, right in zip_longest(first, second, fillvalue=missing):
        if left is missing or right is missing:
            raise ValueError("zip() arguments have different lengths")
        yield cast(T, left), cast(U, right)
