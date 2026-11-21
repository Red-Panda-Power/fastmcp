"""OAuth issuer comparisons must retain the URL's exact path."""

import copy

import pytest
from pydantic import AnyUrl, ValidationError

from mcp.client.auth.exceptions import OAuthFlowError
from mcp.client.auth.utils import validate_authorization_response_iss, validate_metadata_issuer
from mcp.shared.auth import OAuthClientMetadata, OAuthMetadata


def metadata(issuer):
    return OAuthMetadata.model_validate(
        {
            "issuer": issuer,
            "authorization_endpoint": "https://auth.example/authorize",
            "token_endpoint": "https://auth.example/token",
            "authorization_response_iss_parameter_supported": True,
        }
    )


@pytest.mark.parametrize("issuer", ["https://auth.example", "https://auth.example/", "https://auth.example/tenant"])
def test_issuer_round_trips_and_matches_exactly(issuer):
    model = metadata(issuer)
    assert str(model.issuer) == issuer
    assert str(copy.deepcopy(model).issuer) == issuer
    assert OAuthMetadata.model_validate_json(model.model_dump_json()).issuer == model.issuer
    assert model.issuer.path == (None if issuer == "https://auth.example" else issuer[len("https://auth.example") :])
    validate_authorization_response_iss(issuer, model)
    validate_metadata_issuer(model, issuer)
    model.model_json_schema()


def test_issuer_with_and_without_trailing_slash_do_not_match():
    model = metadata("https://auth.example")
    with pytest.raises(OAuthFlowError):
        validate_authorization_response_iss("https://auth.example/", model)
    with pytest.raises(OAuthFlowError):
        validate_metadata_issuer(model, "https://auth.example/")
    assert metadata("https://auth.example").issuer != metadata("https://auth.example/").issuer


def test_redirect_urls_keep_validation_and_url_compatibility():
    model = OAuthClientMetadata(redirect_uris=["http://localhost:3030/callback"])
    assert model.redirect_uris == [AnyUrl("http://localhost:3030/callback")]
    with pytest.raises(ValidationError):
        OAuthClientMetadata(redirect_uris=["invalid"])
