"""Multiple in-memory MCP clients on Python 3.8."""

import pytest

from fastmcp import Client, ClientGroup, FastMCP


@pytest.mark.asyncio
async def test_group_lists_and_calls_namespaced_tools():
    left = FastMCP("left")
    right = FastMCP("right")

    @left.tool
    def add(x: int, y: int) -> int:
        return x + y

    @right.tool
    def greet(name: str) -> str:
        return "Hello " + name

    async with ClientGroup({"left": Client(left), "right": Client(right)}) as group:
        assert {tool.name for tool in await group.list_tools()} == {
            "left_add",
            "right_greet",
        }
        assert (await group.call_tool("left_add", {"x": 2, "y": 3})).data == 5
        assert (
            await group.call_tool("right_greet", {"name": "Ada"})
        ).data == "Hello Ada"
