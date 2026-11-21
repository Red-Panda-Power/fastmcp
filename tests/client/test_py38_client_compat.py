"""Protocol-level compatibility checks for the Python 3.8 client path."""

from __future__ import annotations

from fastmcp import Client, FastMCP


async def test_client_dispatches_all_core_mcp_objects_on_python_38() -> None:
    """The in-memory client must exercise the same protocol boundary as a transport."""
    server = FastMCP("Python 3.8 client")

    @server.tool
    def multiply(left: int, right: int):
        return left * right

    @server.resource("memory://status")
    def status() -> str:
        return "ready"

    @server.prompt
    def greeting(name: str) -> str:
        return f"Hello, {name}!"

    async with Client(server) as client:
        tools = await client.list_tools()
        tool_result = await client.call_tool("multiply", {"left": 6, "right": 7})
        resources = await client.list_resources()
        resource_result = await client.read_resource("memory://status")
        prompts = await client.list_prompts()
        prompt_result = await client.get_prompt("greeting", {"name": "Python 3.8"})

    assert [tool.name for tool in tools] == ["multiply"]
    assert tool_result.content[0].text == "42"
    assert len(resources) == 1
    assert str(resources[0].uri) == "memory://status"
    assert "ready" in str(resource_result[0])
    assert [prompt.name for prompt in prompts] == ["greeting"]
    assert "Hello, Python 3.8!" in str(prompt_result.messages[0].content)
