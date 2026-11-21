"""Construct runtime type aliases on Python 3.8 and newer Python versions."""

import operator
import sys
import typing
from functools import reduce
from typing import Any


class _UnionFactory:
    def __getitem__(self, members: Any) -> Any:
        if not isinstance(members, tuple):
            members = (members,)
        if sys.version_info >= (3, 10):
            return reduce(operator.or_, members)
        return typing.Union[members]


class _RuntimeTyping:
    Union = _UnionFactory()
    if sys.version_info >= (3, 9):
        Dict = dict
        List = list
        Set = set
        Tuple = tuple
        FrozenSet = frozenset
        Type = type
    else:
        Dict = typing.Dict
        List = typing.List
        Set = typing.Set
        Tuple = typing.Tuple
        FrozenSet = typing.FrozenSet
        Type = typing.Type


runtime_typing = _RuntimeTyping()
