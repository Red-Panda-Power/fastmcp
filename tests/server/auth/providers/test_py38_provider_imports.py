"""Python 3.8 imports preserve OAuth client registration validation."""

import pytest
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider


@pytest.mark.asyncio
async def test_in_memory_provider_rejects_unregistered_scopes():
    provider = InMemoryOAuthProvider(
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=["read"]
        )
    )
    client = OAuthClientInformationFull(
        client_id="client",
        redirect_uris=[AnyUrl("http://localhost/callback")],
        scope="write",
    )
    with pytest.raises(ValueError, match="not valid"):
        await provider.register_client(client)
    assert await provider.get_client("client") is None
