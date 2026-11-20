"""Construct the upstream runtime type aliases on both old and new Python."""

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
            # Keep PEP 604 unions on newer Python: SDK callers inspect UnionType.
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
