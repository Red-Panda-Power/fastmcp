"""Exercise real transports and Python 3.8 compatibility paths."""

from __future__ import annotations

import http.server
import ssl
import threading

import anyio
import httpcore2
import httpx2
import pytest
import trustme
from httpx2.websockets._api import aconnect_ws
from httpx2.websockets._transport import ASGIWebSocketTransport
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect


@pytest.fixture
def https_server(tmp_path):
    authority = trustme.CA()
    certificate = authority.issue_cert("localhost")
    ca_file = tmp_path / "ca.pem"
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    authority.cert_pem.write_to_path(ca_file)
    certificate.cert_chain_pems[0].write_to_path(cert_file)
    certificate.private_key_pem.write_to_path(key_file)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "5")
            self.end_headers()
            self.wfile.write(b"hello")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert_file), str(key_file))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, str(ca_file)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_https_verifies_certificate_and_hostname(https_server):
    port, ca_file = https_server
    with httpx2.Client(trust_env=False) as client:
        with pytest.raises(httpx2.ConnectError):
            client.get(f"https://localhost:{port}/")

    context = ssl.create_default_context(cafile=ca_file)
    with httpx2.Client(verify=context, trust_env=False) as client:
        assert client.get(f"https://localhost:{port}/").text == "hello"
        with pytest.raises(httpx2.ConnectError):
            client.get(f"https://127.0.0.1:{port}/")


@pytest.mark.anyio
async def test_async_https_and_custom_ca_environment(https_server, monkeypatch):
    port, ca_file = https_server
    monkeypatch.setenv("SSL_CERT_FILE", ca_file)
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")
    async with httpx2.AsyncClient() as client:
        response = await client.get(f"https://localhost:{port}/")
    assert response.text == "hello"
    assert httpcore2.default_ssl_context().verify_mode == ssl.CERT_REQUIRED


@pytest.mark.anyio
async def test_websocket_send_receive_and_subprotocol():
    async def echo(websocket: WebSocket):
        await websocket.accept(subprotocol="mcp")
        await websocket.send_text(await websocket.receive_text())
        await websocket.close()

    app = Starlette(routes=[WebSocketRoute("/ws", echo)])
    async with httpx2.AsyncClient(transport=ASGIWebSocketTransport(app)) as client:
        async with aconnect_ws("ws://localhost/ws", client, subprotocols=["mcp"]) as socket:
            assert socket.subprotocol == "mcp"
            await socket.send_text("hello")
            assert await socket.receive_text() == "hello"


@pytest.mark.anyio
async def test_cancelled_websocket_closes_server_connection():
    disconnected = anyio.Event()

    async def wait_for_disconnect(websocket: WebSocket):
        await websocket.accept()
        try:
            await websocket.receive_text()
        except WebSocketDisconnect:
            disconnected.set()

    app = Starlette(routes=[WebSocketRoute("/ws", wait_for_disconnect)])
    async with httpx2.AsyncClient(transport=ASGIWebSocketTransport(app)) as client:
        with anyio.move_on_after(0.1) as cancel_scope:
            async with aconnect_ws("ws://localhost/ws", client) as socket:
                await socket.receive_text()
        assert cancel_scope.cancel_called
        with anyio.fail_after(3):
            await disconnected.wait()
