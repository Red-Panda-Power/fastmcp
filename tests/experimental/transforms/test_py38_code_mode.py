"""Real Monty sandbox execution on supported Python versions."""

import importlib.util

import pytest

from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode, MontySandboxProvider


@pytest.mark.skipif(
    importlib.util.find_spec("pydantic_monty") is None,
    reason="the optional code-mode sandbox is not installed",
)
@pytest.mark.asyncio
async def test_monty_executes_a_registered_tool():
    server = FastMCP("code-mode compatibility")

    @server.tool
    def add(x: int, y: int) -> int:
        return x + y

    server.add_transform(CodeMode(sandbox_provider=MontySandboxProvider()))
    result = await server.call_tool(
        "execute", {"code": "return await call_tool('add', {'x': 2, 'y': 3})"}
    )
    assert result.structured_content == {"result": 5}
