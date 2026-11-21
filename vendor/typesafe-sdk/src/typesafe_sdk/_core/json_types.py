"""Shared JSON value types."""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Union

from typing_extensions import TypeAlias

JSONValue: TypeAlias = Union[
    str,
    int,
    float,
    bool,
    List["JSONValue | None"],
    Dict[str, "JSONValue | None"],
]
"""A non-null JSON value, with null permitted inside arrays and objects."""

JSONData: TypeAlias = Optional[JSONValue]
JSONMapping: TypeAlias = Mapping[str, JSONData]
JSONState: TypeAlias = Union[str, Dict[str, JSONData], List[JSONData]]
