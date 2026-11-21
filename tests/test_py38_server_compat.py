"""Runtime regression checks for the Python 3.8 server migration."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import timezone
from typing import Any, cast

import pytest
from mcp_types import TextContent
from pydantic import Field
from typing_extensions import (  # noqa: UP035 - Python 3.8
    Annotated,
    get_args,
    get_origin,
)

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceSecurityError, ValidationError
from fastmcp.server.auth import (
    AccessToken,
    AuthContext,
    require_scopes,
    run_auth_checks,
)
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools.base import default_serializer
from fastmcp.utilities.types import get_function_type_hints


def test_postponed_type_hints_keep_metadata() -> None:
    def sample(
        value: Annotated[list[int] | None, Field(description="items")],
    ) -> int | None:
        return None if value is None else len(value)

    hints = get_function_type_hints(sample)
    assert get_origin(hints["value"]) is Annotated
    assert get_args(hints["value"])[1].description == "items"
    assert type(None) in get_args(hints["return"])


def test_middleware_context_is_frozen_and_keyword_only() -> None:
    context = MiddlewareContext(message="message")
    assert context.timestamp.tzinfo == timezone.utc  # noqa: UP017 - Python 3.8
    assert context.copy(method="tools/call").method == "tools/call"
    with pytest.raises(TypeError):
        cast(Any, MiddlewareContext)("message")
    with pytest.raises(FrozenInstanceError):
        cast(Any, context).method = "tools/call"


def test_unknown_json_values_use_string_fallback() -> None:
    class Value:
        def __str__(self) -> str:
            return "fallback"

    assert default_serializer({"value": Value()}) == '{"value":"fallback"}'


async def test_server_component_execution_and_validation() -> None:
    server = FastMCP("compatibility")

    @server.tool
    def total(values: Annotated[list[int] | None, Field(description="items")]) -> int:
        return sum(values or [])

    @server.resource("demo://fixed")
    def fixed() -> str:
        return "fixed"

    @server.resource("demo://greet/{name}")
    def greeting(name: str) -> str:
        return "hello " + name

    @server.prompt
    def greet(name: str) -> str:
        return "hello " + name

    result = await server.call_tool("total", {"values": [1, 2]})
    assert result.structured_content == {"result": 3}
    with pytest.raises(ValidationError):
        await server.call_tool("total", {"values": ["not-an-integer"]})
    assert (await server.read_resource("demo://fixed")).contents[0].content == "fixed"
    assert (await server.read_resource("demo://greet/Ada")).contents[
        0
    ].content == "hello Ada"
    content = (await server.render_prompt("greet", {"name": "Ada"})).messages[0].content
    assert isinstance(content, TextContent)
    assert content.text == "hello Ada"


async def test_resource_traversal_is_still_rejected() -> None:
    server = FastMCP("security")

    @server.resource("file:///{path*}")
    def read(path: str) -> str:
        return path

    with pytest.raises(ResourceSecurityError):
        await server.read_resource("file:///../secret")


async def test_scope_checks_still_deny_missing_permissions() -> None:
    server = FastMCP("authorization")

    @server.tool
    def protected() -> str:
        return "secret"

    token = AccessToken(token="test", client_id="client", scopes=["read"])
    component = (await server.list_tools())[0]
    context = AuthContext(token=token, component=component)
    assert await run_auth_checks(require_scopes("read"), context)
    assert not await run_auth_checks(require_scopes("write"), context)


async def test_lifespan_composition_cleans_up_in_reverse_order() -> None:
    events: list[str] = []

    @lifespan
    async def left(server: FastMCP):
        events.append("enter-left")
        try:
            yield {"left": 1}
        finally:
            events.append("exit-left")

    @lifespan
    async def right(server: FastMCP):
        events.append("enter-right")
        try:
            yield {"right": 2}
        finally:
            events.append("exit-right")

    async with (left | right)(FastMCP("lifespans")) as state:
        assert state == {"left": 1, "right": 2}
        assert events == ["enter-left", "enter-right"]
    assert events == ["enter-left", "enter-right", "exit-right", "exit-left"]
