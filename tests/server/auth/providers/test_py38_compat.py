"""Python 3.8 regression coverage for authentication providers."""

from typing import Any, cast

import httpx2
import pytest
from pydantic import SecretStr

from fastmcp.server.auth.oidc_proxy import OIDCConfiguration
from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from fastmcp.server.auth.providers.workos import WorkOSTokenVerifier


@pytest.mark.asyncio
async def test_introspection_reuses_an_injected_http_client():
    """Caller-owned clients remain open after token introspection."""

    async def respond(request):
        assert request.url == "https://auth.example.com/introspect"
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx2.Response(
            200,
            json={"active": True, "client_id": "user-1", "scope": "read"},
        )

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    verifier = IntrospectionTokenVerifier(
        introspection_url="https://auth.example.com/introspect",
        client_id="test",
        client_secret="secret",
        http_client=client,
    )

    result = await verifier.verify_token("token")

    assert result is not None
    assert result.client_id == "user-1"
    assert not client.is_closed
    await client.aclose()


def test_py38_auth_runtime_types_load_without_changing_key_pair_api():
    """Python 3.8 imports runtime aliases and retains keyword-only key pairs."""

    assert not OIDCConfiguration(strict=False).strict
    assert WorkOSTokenVerifier(authkit_domain="https://test.authkit.app")

    positional_key_pair = cast(Any, RSAKeyPair)
    with pytest.raises(TypeError):
        positional_key_pair(SecretStr("private"), "public")

    assert (
        RSAKeyPair(private_key=SecretStr("private"), public_key="public").public_key
        == "public"
    )
