"""Behavioral checks for Python 3.8-compatible SDK control flow."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import anyio
import pytest
from mcp_types import (
    CallToolResult,
    CreateMessageRequest,
    CreateMessageRequestParams,
    ElicitRequest,
    ElicitRequestFormParams,
    ErrorData,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    ListRootsRequest,
)
from opentelemetry.trace import StatusCode

from mcp.client.session import ClientRequestContext, ClientSession
from mcp.server import _otel
from mcp.shared.direct_dispatcher import create_direct_dispatcher_pair
from mcp.shared.jsonrpc_dispatcher import JSONRPCDispatcher, progress_token_from_params
from mcp.shared.message import SessionMessage


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (None, None),
        ({}, None),
        ({"_meta": {"progressToken": "abc"}}, "abc"),
        ({"_meta": {"progressToken": 0}}, 0),
        ({"_meta": {"progressToken": True}}, None),
        ({"_meta": {"progressToken": 1.5}}, None),
        ({"_meta": "not a mapping"}, None),
    ],
)
def test_progress_token_requires_a_string_or_non_boolean_integer(params, expected) -> None:
    assert progress_token_from_params(params) == expected


@pytest.mark.anyio
async def test_dispatch_input_request_routes_all_supported_types() -> None:
    expected = {
        "sampling": ErrorData(code=1, message="sampling"),
        "elicitation": ErrorData(code=2, message="elicitation"),
        "roots": ErrorData(code=3, message="roots"),
    }

    async def sampling(_ctx, _params):
        return expected["sampling"]

    async def elicitation(_ctx, _params):
        return expected["elicitation"]

    async def roots(_ctx):
        return expected["roots"]

    client_side, _ = create_direct_dispatcher_pair()
    session = ClientSession(
        dispatcher=client_side,
        sampling_callback=sampling,
        elicitation_callback=elicitation,
        list_roots_callback=roots,
    )
    ctx = ClientRequestContext(session=session, request_id="r-1")
    sampling_request = CreateMessageRequest(params=CreateMessageRequestParams(messages=[], max_tokens=1))
    elicitation_request = ElicitRequest(params=ElicitRequestFormParams(message="name", requested_schema={}))

    assert await session.dispatch_input_request(ctx, sampling_request) is expected["sampling"]
    assert await session.dispatch_input_request(ctx, elicitation_request) is expected["elicitation"]
    assert await session.dispatch_input_request(ctx, ListRootsRequest()) is expected["roots"]


@pytest.mark.anyio
async def test_progress_notifications_ignore_boolean_tokens_and_values() -> None:
    client_send, peer_receive = anyio.create_memory_object_stream(32)
    peer_send, client_receive = anyio.create_memory_object_stream(32)
    client = JSONRPCDispatcher(client_receive, client_send)
    seen = []

    async def on_request(_ctx, _method, _params):
        return {}

    async def on_notify(_ctx, _method, _params):
        pass

    async def on_progress(progress, _total, _message):
        seen.append(progress)

    async def respond():
        request = await peer_receive.receive()
        assert isinstance(request.message, JSONRPCRequest)
        request_id = request.message.id
        for params in (
            {"progressToken": True, "progress": 0.1},
            {"progressToken": request_id, "progress": True},
            {"progressToken": request_id, "progress": 0.5},
        ):
            message = JSONRPCNotification(jsonrpc="2.0", method="notifications/progress", params=params)
            await peer_send.send(SessionMessage(message=message))
        await peer_send.send(SessionMessage(message=JSONRPCResponse(jsonrpc="2.0", id=request_id, result={"ok": True})))

    try:
        async with anyio.create_task_group() as group:
            await group.start(client.run, on_request, on_notify)
            group.start_soon(respond)
            with anyio.fail_after(5):
                assert await client.send_raw_request("ping", None, {"on_progress": on_progress}) == {"ok": True}
            group.cancel_scope.cancel()
    finally:
        for stream in (client_send, peer_receive, peer_send, client_receive):
            stream.close()
    assert seen == [0.5]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("result", "is_error"),
    [
        (CallToolResult(content=[], is_error=True), True),
        ({"isError": True}, True),
        ({"isError": 1}, False),
        ({"is_error": True}, False),
        ({"isError": False}, False),
    ],
)
async def test_telemetry_only_marks_wire_visible_tool_errors(monkeypatch, result, is_error) -> None:
    class Span:
        def __init__(self):
            self.attributes = {}
            self.status = None

        def set_attribute(self, name, value):
            self.attributes[name] = value

        def set_status(self, status):
            self.status = status

    span = Span()

    @contextmanager
    def captured_span(**_kwargs):
        yield span

    async def call_next(_ctx):
        return result

    monkeypatch.setattr(_otel, "otel_span", captured_span)
    ctx = SimpleNamespace(
        method="tools/call", params={"name": "demo"}, protocol_version="2026-07-28", request_id=None, meta=None
    )
    assert await _otel.OpenTelemetryMiddleware()(ctx, call_next) is result
    assert (span.status == StatusCode.ERROR) is is_error
    assert (span.attributes.get("error.type") == "tool_error") is is_error
