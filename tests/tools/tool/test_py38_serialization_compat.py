"""Tool-result alias behavior shared by the Python 3.8 and current stacks."""

# ruff: noqa: UP006, UP007, UP035

from __future__ import annotations

import copy
import json
import sys
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union, cast

import pydantic_core
import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    WrapSerializer,
    model_serializer,
    model_validator,
    with_config,
)
from typing_extensions import Annotated, TypedDict

import fastmcp.tools.base as tool_base
from fastmcp.tools.base import _serialize_to_jsonable
from fastmcp.utilities.types import get_cached_typeadapter


class DefaultModel(BaseModel):
    value: str = Field(serialization_alias="defaultValue")


class FrozenDefaultModel(DefaultModel):
    model_config = ConfigDict(frozen=True)


class AliasModel(BaseModel):
    model_config = ConfigDict(serialize_by_alias=True)

    value: str = Field(serialization_alias="aliasValue")
    default: DefaultModel


class OuterModel(BaseModel):
    value: str = Field(serialization_alias="outerValue")
    nested: AliasModel


class CustomModel(BaseModel):
    value: str = Field(serialization_alias="aliasedValue")

    @model_serializer
    def serialize(self) -> dict[str, str]:
        return {"customValue": self.value}


class AnyPayloadModel(BaseModel):
    payload: Any


class RecursiveAnyModel(BaseModel):
    children: List[RecursiveAnyModel] = Field(default_factory=list)
    payload: Any = None


class AnyTypedDict(TypedDict):
    item: Any


class SecretModel(BaseModel):
    secret: str


class BeforeModel(BaseModel):
    value: str = Field(serialization_alias="renamed")

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data):
        return data


class NullNonfiniteModel(BaseModel):
    model_config = ConfigDict(ser_json_inf_nan="null")

    value: float


class StringNonfiniteModel(BaseModel):
    model_config = ConfigDict(ser_json_inf_nan="strings")

    value: float


@with_config(ConfigDict(serialize_by_alias=True))
@dataclass
class AliasDataclass:
    value: Annotated[str, Field(serialization_alias="dataValue")]


def test_serialization_preserves_each_nested_model_policy():
    value = OuterModel(
        value="outer",
        nested=AliasModel(value="nested", default=DefaultModel(value="default")),
    )

    assert _serialize_to_jsonable([value], List[OuterModel]) == [
        {
            "value": "outer",
            "nested": {
                "aliasValue": "nested",
                "default": {"value": "default"},
            },
        }
    ]


def test_serialization_preserves_policies_in_mappings_and_dataclasses():
    values = {"item": AliasModel(value="nested", default=DefaultModel(value="default"))}

    assert _serialize_to_jsonable(values, Dict[str, AliasModel]) == {
        "item": {
            "aliasValue": "nested",
            "default": {"value": "default"},
        }
    }
    assert _serialize_to_jsonable(
        [AliasDataclass(value="data")], List[AliasDataclass]
    ) == [{"dataValue": "data"}]


def test_serialization_preserves_aliases_in_tuples_and_any_values():
    value = AliasModel(value="nested", default=DefaultModel(value="default"))
    expected = {
        "aliasValue": "nested",
        "default": {"value": "default"},
    }

    assert _serialize_to_jsonable((value, value), Tuple[AliasModel, ...]) == [
        expected,
        expected,
    ]
    assert _serialize_to_jsonable([value], List[Any]) == [expected]


def test_serialization_leaves_custom_model_serializer_output_unchanged():
    value = CustomModel(value="custom")

    assert _serialize_to_jsonable([value], List[CustomModel]) == [
        {"customValue": "custom"}
    ]
    assert _serialize_to_jsonable([value], List[Any]) == [{"customValue": "custom"}]


def test_any_nested_containers_serialize_custom_models_once():
    calls = {"count": 0}

    class CountingModel(BaseModel):
        value: str

        @model_serializer
        def serialize(self) -> dict[str, str]:
            calls["count"] += 1
            return {"call": str(calls["count"]), "value": self.value}

    data = {
        "items": [CountingModel(value="once")],
        "model": AliasModel(value="nested", default=DefaultModel(value="default")),
    }

    assert _serialize_to_jsonable(data, Dict[str, Any]) == {
        "items": [{"call": "1", "value": "once"}],
        "model": {
            "aliasValue": "nested",
            "default": {"value": "default"},
        },
    }
    assert calls == {"count": 1}


def test_any_dispatches_mixed_model_serializers_by_runtime_class():
    calls = {"a": 0, "b": 0}

    class SerializerA(BaseModel):
        value: str

        @model_serializer
        def serialize(self) -> dict[str, str]:
            calls["a"] += 1
            return {"a": self.value}

    class SerializerB(BaseModel):
        value: str

        @model_serializer
        def serialize(self) -> dict[str, str]:
            calls["b"] += 1
            return {"b": self.value}

    assert _serialize_to_jsonable(
        [SerializerA(value="a"), SerializerB(value="b")], List[Any]
    ) == [{"a": "a"}, {"b": "b"}]
    assert calls == {"a": 1, "b": 1}


def test_any_keeps_a_user_plain_serializer_in_control():
    annotation = Annotated[
        Any,
        PlainSerializer(lambda value: "redacted", return_type=str),
    ]

    assert _serialize_to_jsonable(SecretModel(secret="do-not-show"), annotation) == (
        "redacted"
    )


def test_wrap_serializer_handler_keeps_nested_any_alias_policy():
    annotation = Annotated[
        Any,
        WrapSerializer(
            lambda value, handler: {"wrapped": handler(value)},
            return_type=Dict[str, Any],
        ),
    ]

    assert _serialize_to_jsonable(DefaultModel(value="x"), annotation) == {
        "wrapped": {"value": "x"}
    }


def test_plain_serializer_any_return_keeps_nested_alias_policy():
    annotation = Annotated[
        Any,
        PlainSerializer(lambda value: DefaultModel(value="x"), return_type=Any),
    ]

    assert _serialize_to_jsonable("ignored", annotation) == {"value": "x"}


def test_any_dispatch_respects_model_nonfinite_json_policies():
    null_model = NullNonfiniteModel(value=float("nan"))
    string_model = StringNonfiniteModel(value=float("nan"))

    assert _serialize_to_jsonable([null_model, 1], List[Any]) == [
        {"value": None},
        1,
    ]
    assert _serialize_to_jsonable(
        {"model": null_model, "plain": 1}, Dict[str, Any]
    ) == {
        "model": {"value": None},
        "plain": 1,
    }
    assert _serialize_to_jsonable([string_model, 1], List[Any]) == [
        {"value": "NaN"},
        1,
    ]
    assert _serialize_to_jsonable(
        {"model": string_model, "plain": 1}, Dict[str, Any]
    ) == {
        "model": {"value": "NaN"},
        "plain": 1,
    }


def test_any_in_tuple_typed_dict_and_union_preserves_default_alias_policy():
    value = DefaultModel(value="x")

    assert _serialize_to_jsonable((value,), Tuple[Any, ...]) == [{"value": "x"}]
    assert _serialize_to_jsonable({"item": value}, AnyTypedDict) == {
        "item": {"value": "x"}
    }
    assert _serialize_to_jsonable({"item": value}, Union[Dict[str, Any], str]) == {
        "item": {"value": "x"}
    }
    assert _serialize_to_jsonable({FrozenDefaultModel(value="x")}, Any) == [
        {"value": "x"}
    ]


def test_before_model_validator_does_not_restore_default_aliases():
    assert _serialize_to_jsonable(BeforeModel(value="x"), BeforeModel) == {"value": "x"}


def test_model_field_annotated_any_uses_nested_model_alias_policy():
    value = AnyPayloadModel(
        payload=AnyPayloadModel(payload=DefaultModel(value="nested"))
    )

    assert _serialize_to_jsonable(value, AnyPayloadModel) == {
        "payload": {
            "payload": {"value": "nested"},
        }
    }


def test_recursive_model_definition_refs_specialize_any_fields():
    value = RecursiveAnyModel(
        children=[RecursiveAnyModel(payload=DefaultModel(value="nested"))]
    )
    schema = get_cached_typeadapter(RecursiveAnyModel).core_schema

    assert schema["type"] == "definitions"
    assert _serialize_to_jsonable(value, RecursiveAnyModel) == {
        "children": [{"children": [], "payload": {"value": "nested"}}],
        "payload": None,
    }


def test_schema_metadata_with_uncopyable_values_does_not_break_serialization():
    lock = threading.Lock()

    class LockMetadata:
        @classmethod
        def __get_pydantic_core_schema__(cls, source_type, handler):
            schema = handler(source_type)
            schema.setdefault("metadata", {})["lock"] = lock
            return schema

    class LockMetadataModel(BaseModel):
        value: Annotated[str, LockMetadata] = Field(
            json_schema_extra=cast(Any, {"lock": lock})
        )

    with pytest.raises(TypeError):
        copy.deepcopy(get_cached_typeadapter(LockMetadataModel).core_schema)

    assert _serialize_to_jsonable(
        LockMetadataModel(value="safe"), LockMetadataModel
    ) == {"value": "safe"}


def test_cyclic_any_value_raises_pydantic_circular_reference_error():
    value: Dict[str, Any] = {}
    value["self"] = value

    with pytest.raises(ValueError, match="[Cc]ircular reference"):
        _serialize_to_jsonable(value, Any)


def test_recursive_model_cycle_raises_pydantic_circular_reference_error():
    value = RecursiveAnyModel()
    value.children.append(value)

    with pytest.raises(ValueError, match="[Cc]ircular reference"):
        _serialize_to_jsonable(value, RecursiveAnyModel)


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Pydantic 2.10 path")
def test_modern_python_keeps_the_original_serializer(monkeypatch):
    value = AliasModel(value="nested", default=DefaultModel(value="default"))

    def dynamic_serializer_was_called(*args, **kwargs):
        raise AssertionError("modern Python must not build a dynamic Any serializer")

    monkeypatch.setattr(
        tool_base, "_get_dynamic_json_serializer", dynamic_serializer_was_called
    )
    monkeypatch.setattr(
        tool_base,
        "_schema_contains_any",
        dynamic_serializer_was_called,
    )
    expected = json.loads(
        pydantic_core.SchemaSerializer(
            get_cached_typeadapter(AliasModel).core_schema,
            config={"ser_json_inf_nan": "constants"},
        ).to_json(value)
    )
    assert _serialize_to_jsonable(value, AliasModel) == expected
