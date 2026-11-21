"""FastAPI/OpenAPI integration on the Python 3.8 compatibility path."""

from typing import Any, cast

import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.providers.openapi import MCPType, RouteMap


class Widget(BaseModel):
    name: str
    count: int


@pytest.mark.asyncio
async def test_fastapi_models_become_validated_mcp_tools():
    app = FastAPI()
    calls = []

    @app.post("/widgets", operation_id="create_widget")
    def create_widget(widget: Widget) -> Widget:
        calls.append(widget)
        return widget

    server = FastMCP.from_fastapi(app)
    async with Client(server) as client:
        tools = await client.list_tools()
        tool = next(item for item in tools if item.name == "create_widget")
        assert set(tool.input_schema["required"]) == {"name", "count"}
        result = await client.call_tool("create_widget", {"name": "gear", "count": 2})
        assert result.structured_content == {"name": "gear", "count": 2}
        with pytest.raises(ToolError):
            await client.call_tool("create_widget", {"name": "gear", "count": "bad"})

    assert len(calls) == 1


def test_openapi_route_map_requires_keyword_arguments():
    assert RouteMap(mcp_type=MCPType.TOOL).mcp_type is MCPType.TOOL
    with pytest.raises(TypeError):
        cast(Any, RouteMap)(MCPType.TOOL)
