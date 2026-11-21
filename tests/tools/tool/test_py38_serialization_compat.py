"""Tool-result alias behavior shared by the Python 3.8 and current stacks."""

# ruff: noqa: UP006, UP035

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pydantic_core
import pytest
from pydantic import BaseModel, ConfigDict, Field, model_serializer, with_config
from typing_extensions import Annotated

import fastmcp.tools.base as tool_base
from fastmcp.tools.base import _serialize_to_jsonable
from fastmcp.utilities.types import get_cached_typeadapter


class DefaultModel(BaseModel):
    value: str = Field(serialization_alias="defaultValue")


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


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Pydantic 2.10 path")
def test_modern_python_keeps_the_original_any_serializer(monkeypatch):
    value = AliasModel(value="nested", default=DefaultModel(value="default"))

    def dynamic_serializer_was_called(*args, **kwargs):
        raise AssertionError("modern Python must not build a dynamic Any serializer")

    monkeypatch.setattr(
        tool_base, "_get_dynamic_json_serializer", dynamic_serializer_was_called
    )
    expected = json.loads(
        pydantic_core.SchemaSerializer(
            get_cached_typeadapter(Any).core_schema,
            config={"ser_json_inf_nan": "constants"},
        ).to_json(value)
    )
    assert _serialize_to_jsonable(value, Any) == expected
