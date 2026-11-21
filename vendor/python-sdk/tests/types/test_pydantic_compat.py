"""Per-call Pydantic alias controls must work on the Python 3.8 backport."""

import json
import sys
import types
from typing import get_args

import pytest
from pydantic import ConfigDict, Field, PydanticUserError, ValidationError

from mcp_types import CLIENT_CAPABILITIES_META_KEY, PROTOCOL_VERSION_META_KEY, DiscoverRequest, RequestParams
from mcp_types._pydantic_compat import BaseModel, TypeAdapter
from mcp_types.methods import MONOLITH_RESULTS


class Nested(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item_name: str = Field(alias="itemName")


class Container(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nested_item: Nested = Field(alias="nestedItem")


@pytest.mark.parametrize("use_json", [False, True])
def test_alias_only_validation_applies_to_nested_models(use_json: bool) -> None:
    adapter = TypeAdapter(Container)
    valid = {"nestedItem": {"itemName": "ok"}}
    snake_nested = {"nestedItem": {"item_name": "wrong"}}
    validate = adapter.validate_json if use_json else adapter.validate_python
    encode = json.dumps if use_json else lambda value: value

    assert validate(encode(valid), by_name=False).nested_item.item_name == "ok"
    with pytest.raises(ValidationError):
        validate(encode(snake_nested), by_name=False)

    # Per-call overrides must not alter the default model or adapter behavior.
    assert validate(encode(snake_nested)).nested_item.item_name == "wrong"
    assert Container.model_validate(snake_nested).nested_item.item_name == "wrong"


def test_model_alias_override_does_not_change_default_validation() -> None:
    snake = {"nested_item": {"item_name": "ok"}}
    assert Container.model_validate(snake).nested_item.item_name == "ok"
    with pytest.raises(ValidationError):
        Container.model_validate(snake, by_name=False)
    assert Container.model_validate(snake).nested_item.item_name == "ok"


def test_name_only_validation_rejects_aliases() -> None:
    snake = {"nested_item": {"item_name": "ok"}}
    alias = {"nestedItem": {"itemName": "wrong"}}
    assert Container.model_validate(snake, by_alias=False, by_name=True).nested_item.item_name == "ok"
    with pytest.raises(ValidationError):
        Container.model_validate(alias, by_alias=False, by_name=True)


def test_validation_requires_aliases_or_names() -> None:
    with pytest.raises(PydanticUserError):
        Container.model_validate({}, by_alias=False, by_name=False)


def test_runtime_result_unions_keep_the_sdk_representation() -> None:
    result = MONOLITH_RESULTS["tools/call"]
    assert {member.__name__ for member in get_args(result)} == {"CallToolResult", "InputRequiredResult"}
    if sys.version_info >= (3, 10):
        assert isinstance(result, types.UnionType)


def test_request_metadata_preserves_reserved_and_custom_fields() -> None:
    metadata = {
        "progressToken": "progress-1",
        PROTOCOL_VERSION_META_KEY: "2026-07-28",
        CLIENT_CAPABILITIES_META_KEY: {"sampling": {}},
        "example.test/custom": {"value": 3},
    }
    params = RequestParams.model_validate({"_meta": metadata}, by_name=False)
    assert params.meta["progress_token"] == "progress-1"
    assert params.meta["example.test/custom"] == {"value": 3}
    assert params.model_dump(by_alias=True)["_meta"] == metadata

    request = DiscoverRequest(params=params)
    assert request.model_dump(by_alias=True)["params"]["_meta"] == metadata
