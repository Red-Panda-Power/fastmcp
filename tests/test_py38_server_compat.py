"""Runtime regression checks for the Python 3.8 server migration."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import timezone
from typing import Any, Iterator, cast

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
from fastmcp.prompts.base import Prompt
from fastmcp.resources.template import (
    expand_uri_template,
    extract_exploded_query_params,
    match_uri_template,
)
from fastmcp.server.auth import (
    AccessToken,
    AuthContext,
    require_scopes,
    run_auth_checks,
)
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools.base import Tool, default_serializer
from fastmcp.utilities.types import get_function_type_hints, replace_type


def test_postponed_type_hints_keep_metadata() -> None:
    def sample(
        value: Annotated[list[int] | None, Field(description="items")],
    ) -> int | None:
        return None if value is None else len(value)

    hints = get_function_type_hints(sample)
    assert get_origin(hints["value"]) is Annotated
    assert get_args(hints["value"])[1].description == "items"
    assert type(None) in get_args(hints["return"])


def test_replacing_type_in_iterator_alias() -> None:
    result = replace_type(Iterator[int], {int: str})
    assert get_origin(result) is get_origin(Iterator[str])
    assert get_args(result) == (str,)


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


def test_postponed_none_return_has_no_output_schema() -> None:
    def no_result() -> None:
        return None

    assert Tool.from_function(no_result).output_schema is None


def test_prompt_keeps_annotated_parameter_title() -> None:
    def greet(name: Annotated[str, Field(title="Your name")]) -> str:
        return name

    arguments = Prompt.from_function(greet).to_mcp_prompt().arguments or []
    assert [(argument.name, argument.title) for argument in arguments] == [
        ("name", "Your name")
    ]


def test_tool_keeps_explicit_parameter_titles_and_mapping_schema() -> None:
    def greet(
        name: Annotated[str, Field(title="Your name")],
        count: int = Field(default=1, title="Number of greetings"),
    ) -> dict:
        return {"greeting": name * count}

    tool = Tool.from_function(greet)
    properties = tool.parameters["properties"]
    assert properties["name"]["title"] == "Your name"
    assert properties["count"]["title"] == "Number of greetings"
    assert tool.output_schema == {"type": "object", "additionalProperties": True}


def test_exploded_resource_query_round_trips() -> None:
    template = "data://{id}{?x}{&tags*}"
    arguments = {"id": "7", "x": "1", "tags": ["a", "b"]}
    assert extract_exploded_query_params(template) == {"tags"}
    uri = expand_uri_template(template, arguments)
    assert uri == "data://7?x=1&tags=a&tags=b"
    assert match_uri_template(uri, template) == arguments


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
