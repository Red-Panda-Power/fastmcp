"""Compatibility for validation of user-defined Pydantic models and adapters."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp_types import Request
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from mcp.server.connection import Connection, _typed
from mcp.server.session import ServerSession
from mcp.shared._pydantic import validate_adapter, validate_model


class NestedModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="wireName")


class ExternalModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nested: NestedModel = Field(alias="wireNested")


@pytest.mark.parametrize(
    "validator", [validate_model, lambda model, value, **kwargs: validate_adapter(TypeAdapter(model), value, **kwargs)]
)
def test_external_model_validation_uses_wire_aliases(validator):
    result = validator(ExternalModel, {"wireNested": {"wireName": "Ada"}}, by_name=False)
    assert result.nested.name == "Ada"
    with pytest.raises(ValidationError):
        validator(ExternalModel, {"nested": {"name": "Ada"}}, by_name=False)


def test_connection_handles_invalid_custom_model():
    assert _typed(ExternalModel, {"wireNested": {"wireName": "Ada"}}).nested.name == "Ada"
    assert _typed(ExternalModel, {"nested": {"name": "Ada"}}) is None


@pytest.mark.anyio
async def test_server_requests_validate_external_result_models():
    outbound = SimpleNamespace(send_raw_request=AsyncMock(return_value={"wireNested": {"wireName": "Ada"}}))
    connection = Connection.for_loop(outbound)
    session = ServerSession(outbound, connection)
    request = Request(method="example/custom", params=None)

    assert (await connection.send_request(request, result_type=ExternalModel)).nested.name == "Ada"
    assert (await session.send_request(request, ExternalModel)).nested.name == "Ada"

    outbound.send_raw_request.return_value = {"nested": {"name": "Ada"}}
    with pytest.raises(ValidationError):
        await connection.send_request(request, result_type=ExternalModel)
    with pytest.raises(ValidationError):
        await session.send_request(request, ExternalModel)
