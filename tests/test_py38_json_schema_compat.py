"""Regression coverage for Pydantic 2.10 behavior used on Python 3.8."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter

from fastmcp.utilities.json_schema_type import json_schema_to_type


@pytest.mark.parametrize(
    "values",
    [
        [True, 1],
        [False, 0],
        [1.0, True],
        [True, 1.0],
        [0.0, False],
        [False, 0.0],
    ],
)
def test_mixed_boolean_numeric_enum_preserves_schema_value_types(
    values: list[int | float | bool],
) -> None:
    """JSON Schema enums retain boolean and numeric values that compare equal."""
    adapter = TypeAdapter(json_schema_to_type({"enum": values}))

    for value in values:
        result = adapter.validate_python(value)
        assert result == value
        assert type(result) is type(value)

    for expected, actual in zip(values, adapter.json_schema()["enum"]):
        assert actual == expected
        assert type(actual) is type(expected)


def test_deep_acyclic_object_schema_does_not_report_a_cycle() -> None:
    """Pydantic 2.10 accepts a 21-level object graph without defaults."""
    depth = 20
    definitions: dict[str, Any] = {
        f"M{index}": {
            "type": "object",
            "properties": {
                "child": {
                    "anyOf": [
                        {"$ref": f"#/$defs/M{index + 1}"},
                        {"type": "null"},
                    ]
                }
            },
        }
        for index in range(depth)
    }
    definitions[f"M{depth}"] = {
        "type": "object",
        "properties": {"leaf": {"type": "string"}},
    }
    schema = {
        "type": "object",
        "title": "Deep",
        "properties": {"child": {"$ref": "#/$defs/M0"}},
        "$defs": definitions,
    }
    value: dict[str, Any] = {"leaf": "ok"}
    for _ in range(depth):
        value = {"child": value}

    instance = TypeAdapter(json_schema_to_type(schema)).validate_python(
        {"child": value}
    )
    node: Any = instance.child
    for _ in range(depth):
        node = node.child
    assert node.leaf == "ok"


def test_object_property_defaults_still_merge() -> None:
    """Skipping unnecessary wrappers does not skip a schema's real defaults."""
    schema = {
        "type": "object",
        "properties": {
            "config": {
                "type": "object",
                "default": {"left": 1, "right": 2},
                "properties": {
                    "left": {"type": "integer"},
                    "right": {"type": "integer"},
                },
            }
        },
    }

    instance = TypeAdapter(json_schema_to_type(schema)).validate_python(
        {"config": {"right": 3}}
    )

    assert instance.config.left == 1
    assert instance.config.right == 3
