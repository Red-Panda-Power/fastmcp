"""Exercise MCP wire models through FastAPI on the supported interpreter."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_types import JSONRPCRequest


def test_fastapi_round_trips_jsonrpc_request() -> None:
    app = FastAPI()

    @app.post("/mcp")
    def handle_message(message: JSONRPCRequest) -> JSONRPCRequest:
        return message

    request = {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "echo"}}
    with TestClient(app) as client:
        response = client.post("/mcp", json=request)
        schema = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json() == request
    assert schema.status_code == 200
    assert "/mcp" in schema.json()["paths"]


def test_fastapi_rejects_boolean_jsonrpc_request_id() -> None:
    app = FastAPI()

    @app.post("/mcp")
    def handle_message(message: JSONRPCRequest) -> JSONRPCRequest:
        return message

    with TestClient(app) as client:
        response = client.post("/mcp", json={"jsonrpc": "2.0", "id": True, "method": "tools/list"})

    assert response.status_code == 422
