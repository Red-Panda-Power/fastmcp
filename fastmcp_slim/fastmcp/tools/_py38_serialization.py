"""Pydantic Core serialization compatibility for Python 3.8."""

from __future__ import annotations

import json
import sys
from contextvars import ContextVar
from functools import lru_cache
from typing import Any, Dict, FrozenSet, List, Set, Tuple, cast

import pydantic_core
from pydantic import BaseModel
from typing_extensions import get_args

from fastmcp.utilities.types import get_cached_typeadapter

_RUNTIME_ANY_VALUE_IDS = ContextVar(
    "fastmcp_runtime_any_value_ids", default=frozenset()
)


@lru_cache(maxsize=5000)
def _get_json_serializer(annotation: Any) -> pydantic_core.SchemaSerializer:
    """Build a serializer that follows the real JSON serialization contract.

    `ser_json_inf_nan="constants"` keeps non-finite floats as NaN/Infinity JSON
    tokens instead of silently rewriting them to null, so the tokens that reach
    the wire can be rejected at the JSON boundary (see `_reject_nonfinite`).
    The schema is the annotation's own, so custom serializers and explicit
    per-model policies keep control of their output.
    """
    schema = get_cached_typeadapter(annotation).core_schema
    if sys.version_info < (3, 9):  # noqa: UP036 - Python 3.8 compatibility
        schema = _copy_core_schema(schema)
        _remove_serialization_aliases(schema, set())
    return pydantic_core.SchemaSerializer(
        schema, config={"ser_json_inf_nan": "constants"}
    )


def _model_serializes_by_alias(model_type: type[Any]) -> bool:
    """Read a model or dataclass's explicit alias policy.

    Pydantic 2.10 accepts ``serialize_by_alias`` in a model config but its core
    serializer does not honor the setting. Newer Pydantic versions do, with a
    default of ``False``. Keeping that default here gives both dependency lines
    the same public tool-result contract.
    """
    config = getattr(model_type, "model_config", None)
    if config is None:
        config = getattr(model_type, "__pydantic_config__", None)
    if config is None:
        return False
    return config.get("serialize_by_alias") is True


def _remove_model_field_aliases(schema: Any, visited: set[int]) -> None:
    """Remove aliases from one model's fields without changing child models."""
    if isinstance(schema, dict):
        schema_id = id(schema)
        if schema_id in visited:
            return
        visited.add(schema_id)

        schema_type = schema.get("type")
        if isinstance(schema_type, str) and schema_type in {"model", "dataclass"}:
            return
        if isinstance(schema_type, str) and schema_type in {
            "model-fields",
            "dataclass-args",
        }:
            fields = schema.get("fields", {})
            field_values = fields.values() if isinstance(fields, dict) else fields
            for field in field_values:
                if isinstance(field, dict):
                    field.pop("serialization_alias", None)

        for value in schema.values():
            _remove_model_field_aliases(value, visited)
    elif isinstance(schema, (list, tuple)):
        for value in schema:
            _remove_model_field_aliases(value, visited)


def _remove_serialization_aliases(schema: Any, visited: set[int]) -> None:
    """Remove aliases for models that do not explicitly opt into them.

    Pydantic Core 2.27 only accepts a single `by_alias` value for an entire
    serializer tree. Its schema retains each field's serialization alias, so a
    copied schema can express the per-model policy introduced in newer Pydantic
    releases: retain aliases for opt-in models and remove them everywhere else.
    This leaves custom serializers and all non-alias serialization behavior in
    Pydantic Core untouched.
    """
    if isinstance(schema, dict):
        schema_id = id(schema)
        if schema_id in visited:
            return
        visited.add(schema_id)

        schema_type = schema.get("type")
        model_type = schema.get("cls")
        if (
            isinstance(schema_type, str)
            and schema_type in {"model", "dataclass"}
            and isinstance(model_type, type)
            and not _model_serializes_by_alias(model_type)
        ):
            _remove_model_field_aliases(schema.get("schema"), set())

        for value in schema.values():
            _remove_serialization_aliases(value, visited)
    elif isinstance(schema, list):
        for value in schema:
            _remove_serialization_aliases(value, visited)


def _annotation_contains_any(annotation: Any) -> bool:
    """Return whether a serializer schema must dispatch through ``Any``."""
    if annotation is Any:
        return True
    return any(_annotation_contains_any(argument) for argument in get_args(annotation))


def _copy_core_schema(value: Any, memo: dict[int, Any] | None = None) -> Any:
    """Copy mutable Core schema containers without copying user metadata.

    Core schemas may retain arbitrary user metadata, including objects that
    deliberately cannot be deep-copied. Only dict/list/tuple containers are
    changed by the compatibility pass, so opaque values can safely remain the
    original object.
    """
    if memo is None:
        memo = {}

    value_id = id(value)
    if value_id in memo:
        return memo[value_id]

    if isinstance(value, dict):
        copied: dict[Any, Any] = {}
        memo[value_id] = copied
        copied.update(
            (key, _copy_core_schema(item, memo)) for key, item in value.items()
        )
        return copied
    if isinstance(value, list):
        copied_list: list[Any] = []
        memo[value_id] = copied_list
        copied_list.extend(_copy_core_schema(item, memo) for item in value)
        return copied_list
    if isinstance(value, tuple):
        copied_tuple = tuple(_copy_core_schema(item, memo) for item in value)
        memo[value_id] = copied_tuple
        return copied_tuple
    return value


def _schema_contains_any(schema: Any, visited: set[int] | None = None) -> bool:
    """Return whether a Core schema contains an ``Any`` serializer node."""
    if visited is None:
        visited = set()
    if isinstance(schema, dict):
        schema_id = id(schema)
        if schema_id in visited:
            return False
        visited.add(schema_id)
        return schema.get("type") == "any" or any(
            _schema_contains_any(value, visited) for value in schema.values()
        )
    if isinstance(schema, (list, tuple)):
        return any(_schema_contains_any(value, visited) for value in schema)
    return False


def _is_model_value(value: Any) -> bool:
    return isinstance(value, BaseModel) or (
        hasattr(value, "__dataclass_fields__") and not isinstance(value, type)
    )


def _runtime_any_serialization() -> dict[str, Any]:
    """Build the serializer used for an uncustomized runtime ``Any`` value."""
    return {
        "type": "function-plain",
        "function": _serialize_runtime_any_value,
        "return_schema": {"type": "any"},
        "when_used": "json",
    }


def _install_runtime_any_serializers(
    schema: Any, visited: set[int] | None = None
) -> None:
    """Make every uncustomized ``Any`` in a serializer result schema dynamic."""
    if visited is None:
        visited = set()
    if isinstance(schema, dict):
        schema_id = id(schema)
        if schema_id in visited:
            return
        visited.add(schema_id)
        if schema.get("type") == "any" and schema.get("serialization") is None:
            schema["serialization"] = _runtime_any_serialization()
            return
        for value in schema.values():
            _install_runtime_any_serializers(value, visited)
    elif isinstance(schema, (list, tuple)):
        for value in schema:
            _install_runtime_any_serializers(value, visited)


def _serialize_runtime_any_value(value: Any) -> Any:
    """Serialize a model or container reached through an uncustomized ``Any``.

    Pydantic Core's union serializer does not type-dispatch model serializers,
    so a union of two model schemas can call the first model's serializer for
    every value. Building a schema for the actual runtime class avoids that
    ambiguity and keeps each model serializer to one invocation.
    """
    if _is_model_value(value):
        annotation = type(value)
    elif isinstance(value, list):
        annotation = List[Any]
    elif isinstance(value, tuple):
        annotation = Tuple[Any, ...]
    elif isinstance(value, set):
        annotation = Set[Any]
    elif isinstance(value, frozenset):
        annotation = FrozenSet[Any]
    elif isinstance(value, dict):
        annotation = Dict[Any, Any]
    else:
        return value

    active_value_ids = _RUNTIME_ANY_VALUE_IDS.get()
    value_id = id(value)
    if value_id in active_value_ids:
        raise ValueError("Circular reference detected while serializing an Any value")

    token = _RUNTIME_ANY_VALUE_IDS.set(active_value_ids.union({value_id}))
    try:
        if _is_model_value(value) and not _schema_contains_any(
            get_cached_typeadapter(annotation).core_schema
        ):
            serializer = _get_json_serializer(annotation)
        else:
            serializer = _get_dynamic_json_serializer(annotation, value)
        return json.loads(serializer.to_json(value))
    finally:
        _RUNTIME_ANY_VALUE_IDS.reset(token)


def _specialize_model_fields(
    schema: Any,
    instances: list[Any],
    active_value_ids: set[int],
    definitions: dict[str, dict[str, Any]],
) -> None:
    """Follow model wrappers until the model's field schemas are available."""
    while isinstance(schema, dict):
        schema_type = schema.get("type")
        if not isinstance(schema_type, str):
            return
        if schema_type in {"model-fields", "dataclass-args"}:
            fields = schema.get("fields", {})
            field_items = (
                fields.items()
                if isinstance(fields, dict)
                else ((field.get("name"), field) for field in fields)
            )
            for name, field in field_items:
                if not isinstance(name, str) or not isinstance(field, dict):
                    continue
                _specialize_any_schema(
                    field.get("schema"),
                    [
                        getattr(instance, name)
                        for instance in instances
                        if hasattr(instance, name)
                    ],
                    active_value_ids,
                    definitions,
                )
            return
        if schema_type in {
            "function-after",
            "function-before",
            "function-wrap",
            "lax-or-strict",
            "default",
        }:
            schema = schema.get("schema") or schema.get("lax_schema")
        else:
            return


def _specialize_any_schema(
    schema: Any,
    values: list[Any],
    active_value_ids: set[int] | None = None,
    definitions: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Replace Python 3.8 ``Any`` nodes with schemas for their runtime models.

    Pydantic Core 2.27 dispatches an ``Any`` value directly to the model's
    built-in serializer, which unconditionally uses aliases. An uncustomized
    ``Any`` node receives a runtime type-dispatching serializer instead. Nodes
    with their own serializer are intentionally left unchanged: a user
    serializer has priority over this compatibility adaptation.
    """
    if not isinstance(schema, dict) or not values:
        return

    if active_value_ids is None:
        active_value_ids = set()
    if definitions is None:
        definitions = {}

    schema_type = schema.get("type")
    if not isinstance(schema_type, str):
        return
    if schema_type == "any":
        serialization = schema.get("serialization")
        if isinstance(serialization, dict):
            return_schema = serialization.get("return_schema")
            _install_runtime_any_serializers(return_schema)
            if serialization.get("type") == "function-wrap":
                inner_schema = serialization.get("schema")
                if not isinstance(inner_schema, dict):
                    inner_schema = _copy_core_schema(schema)
                    inner_schema.pop("serialization", None)
                    serialization["schema"] = inner_schema
                _specialize_any_schema(
                    inner_schema, values, active_value_ids, definitions
                )
            return
        model_values = [value for value in values if _is_model_value(value)]
        model_types = {type(value) for value in model_values}
        if len(model_values) == len(values) and len(model_types) == 1:
            model_schema = _copy_core_schema(
                get_cached_typeadapter(model_values[0].__class__).core_schema
            )
            _remove_serialization_aliases(model_schema, set())
            _specialize_any_schema(
                model_schema, model_values, active_value_ids, definitions
            )
            schema.clear()
            schema.update(model_schema)
            return
        if any(
            _is_model_value(value)
            or isinstance(value, (list, tuple, set, frozenset, dict))
            for value in values
        ):
            schema["serialization"] = _runtime_any_serialization()
        return

    if schema_type in {"model-field", "default"}:
        _specialize_any_schema(
            schema.get("schema"), values, active_value_ids, definitions
        )
        return

    if schema_type == "definition-ref":
        definition = definitions.get(schema.get("schema_ref"))
        if definition is not None:
            _specialize_any_schema(definition, values, active_value_ids, definitions)
        return

    if schema_type in {
        "function-after",
        "function-before",
        "function-wrap",
        "lax-or-strict",
    }:
        _specialize_any_schema(
            schema.get("schema") or schema.get("lax_schema"),
            values,
            active_value_ids,
            definitions,
        )
        return

    if schema_type == "json-or-python":
        _specialize_any_schema(
            schema.get("python_schema"), values, active_value_ids, definitions
        )
        return

    if schema_type == "chain":
        for step in schema.get("steps", []):
            _specialize_any_schema(step, values, active_value_ids, definitions)
        return

    if schema_type == "union":
        for choice in schema.get("choices", []):
            choice_schema = choice[0] if isinstance(choice, tuple) else choice
            _specialize_any_schema(choice_schema, values, active_value_ids, definitions)
        return

    if schema_type in {"list", "set", "frozenset"}:
        container_ids = {
            id(value)
            for value in values
            if isinstance(value, (list, tuple, set, frozenset))
        }
        if active_value_ids.intersection(container_ids):
            # Leave a cycle to Pydantic Core's normal circular-reference
            # handling. Recursing here would only loop while specializing.
            return
        active_value_ids = active_value_ids.union(container_ids)
        items = [
            item
            for value in values
            if isinstance(value, (list, tuple, set, frozenset))
            for item in value
        ]
        _specialize_any_schema(
            schema.get("items_schema"), items, active_value_ids, definitions
        )
        return

    if schema_type == "tuple-variable":
        items = [item for value in values if isinstance(value, tuple) for item in value]
        _specialize_any_schema(
            schema.get("items_schema"), items, active_value_ids, definitions
        )
        return

    if schema_type == "tuple":
        tuple_values = [value for value in values if isinstance(value, tuple)]
        item_schemas = schema.get("items_schema", [])
        variadic_item_index = schema.get("variadic_item_index")
        if isinstance(variadic_item_index, int) and variadic_item_index < len(
            item_schemas
        ):
            _specialize_any_schema(
                item_schemas[variadic_item_index],
                [
                    item
                    for value in tuple_values
                    for item in value[variadic_item_index:]
                ],
                active_value_ids,
                definitions,
            )
            return
        for index, item_schema in enumerate(item_schemas):
            _specialize_any_schema(
                item_schema,
                [value[index] for value in tuple_values if len(value) > index],
                active_value_ids,
                definitions,
            )
        return

    if schema_type == "tuple-positional":
        tuple_values = [value for value in values if isinstance(value, tuple)]
        for index, item_schema in enumerate(schema.get("items_schema", [])):
            _specialize_any_schema(
                item_schema,
                [value[index] for value in tuple_values if len(value) > index],
                active_value_ids,
                definitions,
            )
        return

    if schema_type == "dict":
        container_ids = {id(value) for value in values if isinstance(value, dict)}
        if active_value_ids.intersection(container_ids):
            # See the corresponding list handling above.
            return
        active_value_ids = active_value_ids.union(container_ids)
        items = [
            item
            for value in values
            if isinstance(value, dict)
            for item in value.values()
        ]
        _specialize_any_schema(
            schema.get("values_schema"), items, active_value_ids, definitions
        )
        return

    if schema_type == "typed-dict":
        fields = schema.get("fields", {})
        if not isinstance(fields, dict):
            return
        for name, field in fields.items():
            if not isinstance(name, str) or not isinstance(field, dict):
                continue
            _specialize_any_schema(
                field.get("schema"),
                [
                    value[name]
                    for value in values
                    if isinstance(value, dict) and name in value
                ],
                active_value_ids,
                definitions,
            )
        return

    if schema_type in {"model", "dataclass"}:
        model_type = schema.get("cls")
        instances = [
            value
            for value in values
            if isinstance(model_type, type) and isinstance(value, model_type)
        ]
        instance_ids = {id(instance) for instance in instances}
        if active_value_ids.intersection(instance_ids):
            # See the corresponding list handling above.
            return
        active_value_ids = active_value_ids.union(instance_ids)
        _specialize_model_fields(
            schema.get("schema"), instances, active_value_ids, definitions
        )
        return

    if schema_type == "nullable":
        _specialize_any_schema(
            schema.get("schema"),
            [value for value in values if value is not None],
            active_value_ids,
            definitions,
        )
        return

    if schema_type == "definitions":
        local_definitions = definitions.copy()
        for definition in schema.get("definitions", []):
            if isinstance(definition, dict) and isinstance(definition.get("ref"), str):
                local_definitions[definition["ref"]] = definition
        _specialize_any_schema(
            schema.get("schema"), values, active_value_ids, local_definitions
        )


def _get_dynamic_json_serializer(
    annotation: Any, data: Any
) -> pydantic_core.SchemaSerializer:
    """Build a one-off Python 3.8 serializer for runtime ``Any`` values."""
    schema = _copy_core_schema(get_cached_typeadapter(annotation).core_schema)
    _remove_serialization_aliases(schema, set())
    _specialize_any_schema(schema, [data])
    return pydantic_core.SchemaSerializer(
        schema, config={"ser_json_inf_nan": "constants"}
    )


def _get_homogeneous_any_list_serializer(
    annotation: Any, data: Any
) -> pydantic_core.SchemaSerializer | None:
    """Reuse a compiled serializer for ``List[Any]`` of one simple model type.

    This narrow fast path is equivalent to the runtime ``Any`` dispatch but
    avoids calling a Python serializer once per list item. Models whose own
    schema contains ``Any`` still need per-value specialization.
    """
    if annotation != List[Any] or not isinstance(data, list) or not data:
        return None
    if not all(_is_model_value(value) for value in data):
        return None
    model_type = type(data[0])
    if not all(type(value) is model_type for value in data):
        return None
    if _schema_contains_any(get_cached_typeadapter(model_type).core_schema):
        return None
    runtime_annotation = cast(Any, List).copy_with((model_type,))
    return _get_json_serializer(runtime_annotation)
