"""Tool-result alias behavior shared by the Python 3.8 and current stacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_serializer, with_config
from typing_extensions import Annotated

from fastmcp.tools.base import _serialize_to_jsonable


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
