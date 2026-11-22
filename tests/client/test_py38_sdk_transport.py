"""Exercise SDK transports and result claims with the Python 3.8 runtime."""

from __future__ import annotations

import sys
from typing import Literal

import pytest
from mcp.client.extension import ClaimContext, ResultClaim
from mcp_types import CallToolResult, Result

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


class CustomResult(Result):
    result_type: Literal["internal/custom"]
    value: str


async def _resolve_result(result: CustomResult, ctx: ClaimContext) -> CallToolResult:
    return CallToolResult(content=[])


async def _resolve_core(result: CallToolResult, ctx: ClaimContext) -> CallToolResult:
    return result


def test_extension_claim_accepts_custom_result() -> None:
    claim = ResultClaim(
        result_type="internal/custom", model=CustomResult, resolve=_resolve_result
    )
    assert claim.model is CustomResult

    with pytest.raises(ValueError, match="must not subclass core result types"):
        ResultClaim(
            result_type="internal/custom", model=CallToolResult, resolve=_resolve_core
        )


async def test_stdio_client_passes_environment_to_server(tmp_path) -> None:
    server = tmp_path / "server.py"
    server.write_text(
        "import os\n"
        "from fastmcp import FastMCP\n"
        "mcp = FastMCP('stdio')\n"
        "@mcp.tool\n"
        "def read_environment() -> str:\n"
        "    return os.environ['FASTMCP_STDIO_TEST']\n"
        "if __name__ == '__main__':\n"
        "    mcp.run()\n",
        encoding="utf-8",
    )
    transport = StdioTransport(
        command=sys.executable,
        args=[str(server)],
        env={"FASTMCP_STDIO_TEST": "present"},
        keep_alive=False,
    )
    async with Client(transport) as client:
        assert (await client.call_tool("read_environment", {})).data == "present"
