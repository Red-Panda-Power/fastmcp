"""SSRF behavior on the Python 3.8 compatibility path."""

import asyncio
from unittest.mock import AsyncMock

import httpx2
import pytest

import fastmcp
from fastmcp.server.auth import ssrf


@pytest.mark.asyncio
async def test_fetch_pins_host_and_disables_redirects(monkeypatch):
    monkeypatch.setattr(fastmcp.settings, "ssrf_trust_proxy", False)
    monkeypatch.setattr(ssrf, "resolve_hostname", AsyncMock(return_value=["8.8.8.8"]))
    requests = []
    options = []
    original_client = httpx2.AsyncClient

    def handler(request):
        requests.append(request)
        return httpx2.Response(200, content=b"ok")

    def client_factory(**kwargs):
        options.append(kwargs.copy())
        return original_client(transport=httpx2.MockTransport(handler), **kwargs)

    monkeypatch.setattr(ssrf.httpx2, "AsyncClient", client_factory)
    response = await ssrf.ssrf_safe_fetch_response(
        "https://example.com/test", request_headers={"Host": "attacker.invalid"}
    )
    assert response.content == b"ok"
    assert requests[0].url.host == "8.8.8.8"
    assert requests[0].headers["host"] == "example.com"
    assert options[0]["follow_redirects"] is False
    assert options[0]["verify"] is True


@pytest.mark.asyncio
async def test_private_address_and_oversized_body_are_rejected(monkeypatch):
    monkeypatch.setattr(fastmcp.settings, "ssrf_trust_proxy", False)
    monkeypatch.setattr(ssrf, "resolve_hostname", AsyncMock(return_value=["127.0.0.1"]))
    with pytest.raises(ssrf.SSRFError, match="blocked IP"):
        await ssrf.validate_url("https://example.com/test")

    monkeypatch.setattr(ssrf, "resolve_hostname", AsyncMock(return_value=["8.8.8.8"]))
    original_client = httpx2.AsyncClient

    def client_factory(**kwargs):
        return original_client(
            transport=httpx2.MockTransport(
                lambda request: httpx2.Response(200, content=b"long")
            ),
            **kwargs,
        )

    monkeypatch.setattr(ssrf.httpx2, "AsyncClient", client_factory)
    with pytest.raises(ssrf.SSRFFetchError, match="too large"):
        await ssrf.ssrf_safe_fetch("https://example.com/test", max_size=2)


@pytest.mark.asyncio
async def test_overall_timeout_uses_public_fetch_error(monkeypatch):
    monkeypatch.setattr(
        ssrf,
        "_ssrf_safe_fetch_response",
        AsyncMock(side_effect=asyncio.TimeoutError()),  # noqa: UP041 - Python 3.8
    )
    with pytest.raises(ssrf.SSRFFetchError, match="Overall timeout"):
        await ssrf.ssrf_safe_fetch_response("https://example.com/test")
