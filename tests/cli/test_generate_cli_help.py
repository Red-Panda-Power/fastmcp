"""Generated parameter help must preserve descriptions as Python string literals."""

# Runtime type aliases keep these locally defined callables evaluable on Python 3.8.
# ruff: noqa: UP006, UP035, UP045

from typing import Any, Dict, List, Optional, Tuple

import pytest
from pydantic import Field
from typing_extensions import Annotated, get_type_hints  # noqa: UP035

from fastmcp import Client, FastMCP
from fastmcp.cli.generate import generate_cli_script


@pytest.mark.parametrize("newline", ["\r\n", "\r", "\n"])
async def test_parameter_help_preserves_line_endings(newline: str) -> None:
    description = f"First \"line\"{newline}Second 'line' at C:\\tools — 설명"
    server = FastMCP("Descriptions")
    received: List[Tuple[str, Dict[str, str], str, Optional[Dict[str, str]]]] = []

    @server.tool
    def record(
        message: Annotated[str, Field(description=description)],
        options: Annotated[Dict[str, str], Field(description=description)] = {"x": "y"},
        label: Annotated[str, Field(description=description)] = "default",
        optional: Annotated[
            Optional[Dict[str, str]], Field(description=description)
        ] = None,
    ) -> None:
        received.append((message, options, label, optional))

    async with Client(server) as client:
        tools = await client.list_tools()
    script = generate_cli_script(
        server_name="descriptions",
        server_spec="descriptions",
        transport_code=repr("http://unused/mcp"),
        extra_imports=set(),
        tools=tools,
    )
    namespace: Dict[str, Any] = {"__name__": "generated_cli"}
    exec(compile(script, "<generated>", "exec"), namespace)
    namespace["CLIENT_SPEC"] = server
    app = namespace["app"]
    # Python 3.10's get_type_hints adds Optional around parameters defaulted to None.
    annotations = get_type_hints(
        app["call-tool"]["record"].default_command, include_extras=True
    )
    for name in ("message", "label"):
        assert annotations[name].__metadata__[0].help == description
    for name in ("options", "optional"):
        assert annotations[name].__metadata__[0].help.startswith(description)

    await app.run_async(
        ["call-tool", "record", "--message", "hello"], result_action="return_value"
    )
    await app.run_async(
        [
            "call-tool",
            "record",
            "--message",
            "hi",
            "--options",
            '{"a": "b"}',
            "--label",
            "override",
            "--optional",
            '{"z": "q"}',
        ],
        result_action="return_value",
    )
    assert received == [
        ("hello", {"x": "y"}, "default", None),
        ("hi", {"a": "b"}, "override", {"z": "q"}),
    ]


@pytest.mark.parametrize("newline", ["\r\n", "\r", "\n"])
async def test_parameter_help_preserves_explicit_flags(newline: str) -> None:
    description = f"First \"line\"{newline}Second 'line' at C:\\tools — 설명"
    server = FastMCP("Flag descriptions")
    received: List[Tuple[str, str, Dict[str, str], str, Optional[Dict[str, str]]]] = []

    @server.tool(name="app")
    def record(
        user_id: str,
        userId: Annotated[str, Field(description=description)],
        meta_data: Dict[str, str] = {"x": "y"},
        metaData: Annotated[Dict[str, str], Field(description=description)] = {
            "x": "y"
        },
        option_name: str = "default",
        optionName: Annotated[str, Field(description=description)] = "default",
        extra_data: Optional[Dict[str, str]] = None,
        extraData: Annotated[
            Optional[Dict[str, str]], Field(description=description)
        ] = None,
    ) -> None:
        received.append((user_id, userId, metaData, optionName, extraData))

    async with Client(server) as client:
        tools = await client.list_tools()
    script = generate_cli_script(
        server_name="Flag descriptions",
        server_spec="descriptions",
        transport_code=repr("http://unused/mcp"),
        extra_imports=set(),
        tools=tools,
    )
    namespace: Dict[str, Any] = {"__name__": "generated_cli"}
    exec(compile(script, "<generated>", "exec"), namespace)
    namespace["CLIENT_SPEC"] = server
    app = namespace["app"]
    annotations = get_type_hints(
        app["call-tool"]["app"].default_command, include_extras=True
    )
    for name in ("userId", "optionName"):
        assert annotations[name].__metadata__[0].help == description
    for name in ("metaData", "extraData"):
        assert annotations[name].__metadata__[0].help.startswith(description)

    await app.run_async(
        ["call-tool", "app", "--user-id", "snake", "--userId", "camel"],
        result_action="return_value",
    )
    await app.run_async(
        [
            "call-tool",
            "app",
            "--user-id",
            "s",
            "--userId",
            "c",
            "--metaData",
            '{"a": "b"}',
            "--optionName",
            "override",
            "--extraData",
            '{"z": "q"}',
        ],
        result_action="return_value",
    )
    assert received == [
        ("snake", "camel", {"x": "y"}, "default", None),
        ("s", "c", {"a": "b"}, "override", {"z": "q"}),
    ]
