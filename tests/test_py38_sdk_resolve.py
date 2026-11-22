"""Resolver metadata remains visible under Python 3.8 type-hint evaluation."""

from __future__ import annotations

from mcp.server.mcpserver.resolve import Resolve, find_resolved_parameters
from mcp.server.mcpserver.utilities.func_metadata import _returns_content
from mcp_types import TextContent
from typing_extensions import Annotated


def _resolve_values():
    return [1]


def test_postponed_modern_annotations_keep_resolver_metadata() -> None:
    def tool(values: Annotated[list[int] | None, Resolve(_resolve_values)]) -> str:
        return str(values)

    parameters = find_resolved_parameters(tool)
    assert parameters["values"][0].fn is _resolve_values


def test_annotated_content_is_recognized_without_json_schema() -> None:
    assert _returns_content(Annotated[TextContent, "metadata"])
