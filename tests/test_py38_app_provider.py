"""Python 3.8 coverage for FastMCPApp's renderer-independent provider path."""

from __future__ import annotations

import pytest

from fastmcp import Client, FastMCP, FastMCPApp
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import require_scopes
from fastmcp.server.providers.addressing import hashed_backend_name


async def test_app_backend_tool_works_without_renderer() -> None:
    calls: list[str] = []
    app = FastMCPApp("reports")

    @app.tool()
    def lookup(report_id: str) -> str:
        calls.append(report_id)
        return f"report:{report_id}"

    server = FastMCP("Reports")
    server.add_provider(app)

    async with Client(server) as client:
        listed_tools = {tool.name: tool for tool in await client.list_tools()}
        assert listed_tools["lookup"].meta["ui"]["visibility"] == ["app"]
        result = await client.call_tool(
            hashed_backend_name("reports", "lookup"), {"report_id": "r-1"}
        )

    assert result.data == "report:r-1"
    assert calls == ["r-1"]


async def test_app_backend_tool_auth_is_enforced() -> None:
    calls: list[str] = []
    app = FastMCPApp("admin")

    @app.tool(auth=require_scopes("reports:write"))
    def delete_report(report_id: str) -> str:
        calls.append(report_id)
        return f"deleted:{report_id}"

    server = FastMCP("Reports")
    server.add_provider(app)

    async with Client(server) as client:
        with pytest.raises(ToolError, match="Unknown tool"):
            await client.call_tool(
                hashed_backend_name("admin", "delete_report"),
                {"report_id": "r-1"},
            )

    assert calls == []
