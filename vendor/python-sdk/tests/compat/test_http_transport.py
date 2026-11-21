"""Exercise the vendored SDK over a real local HTTP connection."""

import socket
import threading
import time

import httpx2
import pytest
import uvicorn

from mcp.client import Client
from mcp.server.mcpserver import MCPServer


@pytest.fixture
def http_server():
    mcp = MCPServer("python38-http")

    @mcp.tool()
    def add(a: int, b: int) -> int:
        return a + b

    app = mcp.streamable_http_app(host="127.0.0.1")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", ws="none", lifespan="on"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() >= deadline:
                raise RuntimeError("HTTP test server failed to start")
            time.sleep(0.01)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive()


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_streamable_http_round_trip(http_server, mode):
    async with Client(http_server, mode=mode) as client:
        assert [tool.name for tool in (await client.list_tools()).tools] == ["add"]
        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert not result.is_error
        assert result.content[0].text == "5"


@pytest.mark.anyio
async def test_http_rejects_untrusted_host(http_server):
    async with httpx2.AsyncClient(trust_env=False) as client:
        response = await client.post(
            http_server,
            headers={"Host": "untrusted.example", "Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        )
    assert response.status_code == 421 or response.status_code == 403
