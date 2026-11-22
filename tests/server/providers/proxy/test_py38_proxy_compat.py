"""Proxy all core component types over the Python 3.8 protocol stack."""

import pytest

from fastmcp import Client, FastMCP
from fastmcp.client import dependencies
from fastmcp.server.providers.proxy import ProxyProvider


def test_configured_headers_override_forwarded_headers(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "_get_forwardable_http_headers",
        lambda: {"authorization": "Bearer old", "x-tenant": "internal"},
    )
    assert dependencies._merge_forwardable_http_headers(
        {"Authorization": "Bearer new"}
    ) == {"Authorization": "Bearer new", "x-tenant": "internal"}


@pytest.mark.asyncio
async def test_proxy_forwards_tools_resources_templates_and_prompts():
    backend = FastMCP("backend")

    @backend.tool
    def add(a: int, b: int) -> int:
        return a + b

    @backend.resource("resource://hello")
    def resource() -> str:
        return "hello"

    @backend.resource("resource://greet/{name}")
    def template(name: str) -> str:
        return "Hello " + name

    @backend.prompt
    def greet(name: str) -> str:
        return "Hello " + name

    proxy = FastMCP("proxy", providers=[ProxyProvider(lambda: Client(backend))])
    async with Client(proxy) as client:
        assert [tool.name for tool in await client.list_tools()] == ["add"]
        assert (await client.call_tool("add", {"a": 1, "b": 2})).data == 3
        assert (await client.read_resource("resource://hello"))[0].text == "hello"
        assert (await client.read_resource("resource://greet/Ada"))[
            0
        ].text == "Hello Ada"
        prompt = await client.get_prompt("greet", {"name": "Ada"})
        assert prompt.messages[0].content.text == "Hello Ada"
