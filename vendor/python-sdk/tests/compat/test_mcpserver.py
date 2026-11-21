"""Exercise the public MCP server surfaces over both protocol paths."""

import pytest
from mcp_types import TextContent, TextResourceContents

from mcp.client import Client
from mcp.server.mcpserver import MCPServer


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_tools_resources_templates_and_prompts_round_trip(mode):
    server = MCPServer("python38-compatibility")

    @server.tool()
    def add(a: int, b: int) -> int:
        return a + b

    @server.resource("config://settings")
    def settings() -> str:
        return "ready"

    @server.resource("file://documents/{name}")
    def document(name: str) -> str:
        return "document: " + name

    @server.prompt()
    def greet(name: str) -> str:
        return "hello " + name

    async with Client(server, mode=mode) as client:
        assert [item.name for item in (await client.list_tools()).tools] == ["add"]
        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert not result.is_error
        assert isinstance(result.content[0], TextContent)
        assert result.content[0].text == "5"

        invalid = await client.call_tool("add", {"a": "invalid", "b": 3})
        assert invalid.is_error

        static = await client.read_resource("config://settings")
        assert isinstance(static.contents[0], TextResourceContents)
        assert static.contents[0].text == "ready"
        dynamic = await client.read_resource("file://documents/report")
        assert dynamic.contents[0].text == "document: report"

        assert [item.name for item in (await client.list_prompts()).prompts] == ["greet"]
        prompt = await client.get_prompt("greet", {"name": "Ada"})
        assert prompt.messages[0].content.text == "hello Ada"


@pytest.mark.anyio
async def test_postponed_modern_annotations_are_evaluated():
    server = MCPServer("postponed-annotations")

    @server.tool()
    def total(values: "list[int] | None" = None) -> int:
        return sum(values or [])

    async with Client(server) as client:
        result = await client.call_tool("total", {"values": [1, 2, 3]})
        assert not result.is_error
        assert result.content[0].text == "6"

        invalid = await client.call_tool("total", {"values": ["invalid"]})
        assert invalid.is_error
