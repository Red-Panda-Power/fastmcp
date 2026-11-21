"""Runtime JSON Schema conversion checks for the Python 3.8 backport."""

import pytest
from pydantic import TypeAdapter, ValidationError

from fastmcp.utilities.json_schema_type import json_schema_to_type


def test_object_with_optional_property_before_required_property():
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
        "required": ["count"],
    }
    converted = json_schema_to_type(schema)
    validator = TypeAdapter(converted)
    value = validator.validate_python({"count": 2})
    assert value.count == 2
    assert value.name is None
    with pytest.raises(ValidationError):
        validator.validate_python({"name": "missing count"})
    with pytest.raises(TypeError):
        converted(2)


def test_typed_dictionary_validates_additional_properties():
    validator = TypeAdapter(
        json_schema_to_type(
            {"type": "object", "additionalProperties": {"type": "integer"}}
        )
    )
    assert validator.validate_python({"count": 3}) == {"count": 3}
    with pytest.raises(ValidationError):
        validator.validate_python({"count": "bad"})


def test_array_prefix_items_validate_each_position():
    validator = TypeAdapter(
        json_schema_to_type(
            {
                "type": "array",
                "prefixItems": [{"type": "string"}, {"type": "integer"}],
                "minItems": 2,
                "items": False,
            }
        )
    )
    assert list(validator.validate_python(["a", 2])) == ["a", 2]
    with pytest.raises(ValidationError):
        validator.validate_python(["a", "bad"])


def test_array_rejects_invalid_item_types():
    validator = TypeAdapter(
        json_schema_to_type({"type": "array", "items": {"type": "string"}})
    )
    assert validator.validate_python(["a", "b"]) == ["a", "b"]
    with pytest.raises(ValidationError):
        validator.validate_python(["a", 1])
