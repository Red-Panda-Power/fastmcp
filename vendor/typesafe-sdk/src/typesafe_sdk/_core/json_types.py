"""Shared JSON value types."""

from __future__ import annotations

from typing import Dict, List, Union

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
