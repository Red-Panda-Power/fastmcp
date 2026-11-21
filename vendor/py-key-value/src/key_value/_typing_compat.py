"""Runtime typing aliases that preserve native annotations on newer Python."""

import operator
import sys
import typing
from collections import abc
from functools import reduce
from types import MappingProxyType
from typing import Any


class _UnionFactory:
    def __getitem__(self, members: Any) -> Any:
        if not isinstance(members, tuple):
            members = (members,)
        if sys.version_info >= (3, 10):
            try:
                return reduce(operator.or_, members)
            except TypeError:
                pass
        return typing.Union[members]


class _RuntimeTyping:
    Union = _UnionFactory()
    if sys.version_info >= (3, 9):
        Dict = dict
        List = list
        Set = set
        Tuple = tuple
        Type = type
        Mapping = abc.Mapping
        MappingProxyType = MappingProxyType
        Sequence = abc.Sequence
        Callable = abc.Callable
        Awaitable = abc.Awaitable
        AsyncGenerator = abc.AsyncGenerator
        Iterable = abc.Iterable
        Iterator = abc.Iterator
    else:
        Dict = typing.Dict
        List = typing.List
        Set = typing.Set
        Tuple = typing.Tuple
        Type = typing.Type
        Mapping = typing.Mapping
        MappingProxyType = typing.Mapping
        Sequence = typing.Sequence
        Callable = typing.Callable
        Awaitable = typing.Awaitable
        AsyncGenerator = typing.AsyncGenerator
        Iterable = typing.Iterable
        Iterator = typing.Iterator


runtime_typing = _RuntimeTyping()
