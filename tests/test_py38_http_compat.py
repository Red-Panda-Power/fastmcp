"""Authenticated HTTP execution on the Python 3.8 compatibility path."""

import asyncio
import socket
from contextlib import suppress

import anyio
import httpx2
import pytest
import uvicorn

from fastmcp import Client, FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.utilities.tests import asgi_server


@pytest.mark.asyncio
async def test_http_authentication_and_tool_execution():
    verifier = StaticTokenVerifier(
        {"valid-token": {"client_id": "internal-client", "scopes": ["read"]}}
    )
    server = FastMCP("internal", auth=verifier)

    @server.tool
    def add(a: int, b: int) -> int:
        return a + b

    async with asgi_server(server) as running_server:
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=running_server.app),
            base_url="http://127.0.0.1",
        ) as raw_client:
            response = await raw_client.post("/mcp")
            assert response.status_code == 401
            assert "www-authenticate" in response.headers

        async with running_server.client(auth="valid-token") as client:
            assert (await client.call_tool("add", {"a": 2, "b": 3})).data == 5


async def test_uvicorn_http_server_runs_with_installed_websocket_backend(monkeypatch):
    verifier = StaticTokenVerifier({"valid-token": {"client_id": "internal-client"}})
    server = FastMCP("internal", auth=verifier)

    @server.tool
    def add(a: int, b: int) -> int:
        return a + b

    servers = []

    class TestServer(uvicorn.Server):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            servers.append(self)

    monkeypatch.setattr(uvicorn, "Server", TestServer)

    with socket.socket() as listening_socket:
        listening_socket.bind(("127.0.0.1", 0))
        listening_socket.listen()
        port = listening_socket.getsockname()[1]
        task = asyncio.create_task(
            server.run_http_async(
                host="127.0.0.1",
                port=port,
                sockets=[listening_socket],
                show_banner=False,
            )
        )
        try:
            async with httpx2.AsyncClient() as http_client:
                with anyio.fail_after(15):
                    while True:
                        if task.done():
                            task.result()
                        try:
                            response = await http_client.post(
                                f"http://127.0.0.1:{port}/mcp"
                            )
                        except httpx2.ConnectError:
                            await asyncio.sleep(0.05)
                        else:
                            break
            assert response.status_code == 401
            async with Client(
                f"http://127.0.0.1:{port}/mcp", auth="valid-token"
            ) as client:
                assert (await client.call_tool("add", {"a": 2, "b": 3})).data == 5
        finally:
            if servers:
                servers[0].should_exit = True
                with anyio.fail_after(10):
                    await task
            else:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
