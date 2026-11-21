"""Runtime compatibility checks for the Python 3.8 backport.

These tests deliberately live outside the upstream ``tests`` package: that
package's test annotations target Python 3.10, while this module is executed
on both Python 3.8 and current Python.
"""

import json

import httpx2
import pytest

from typesafe_sdk import (
    AsyncTypeSafeClient,
    RetryPolicy,
    TypeSafeAuthenticationError,
    TypeSafeClient,
)


def _answer_body():
    return {
        "model": "jev-test",
        "usage": {"input_tokens": 3, "output_tokens": 2},
        "answers": {
            "which": {
                "type": "choice",
                "choice": "search",
                "confidence": 0.9,
                "probabilities": {"search": 0.9, "write": 0.1},
            },
            "fits::search": {"type": "noul", "noul": 0.95},
        },
    }


def _questions():
    return {
        "which": {
            "type": "choice",
            "instructions": "Choose the best tool.",
            "criteria": {"search": "find", "write": "create"},
        },
        "fits::search": {"type": "noul", "instructions": "Does it fit?"},
    }


def test_sync_system_one_sends_authentication_and_decodes_j_ev_response():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json=_answer_body())

    with TypeSafeClient(
        api_key="secret-token",
        base_url="https://internal.example",
        transport=httpx2.MockTransport(handler),
    ) as client:
        response = client.system_one({"request": "find records"}, _questions())

    assert response.choices["which"].choice == "search"
    assert response.nouls["fits::search"].noul == 0.95
    assert seen[0].url == "https://internal.example/v1/systemone"
    assert seen[0].headers["authorization"] == "Bearer secret-token"
    assert json.loads(seen[0].content) == {
        "model": "jev-latest",
        "questions": _questions(),
        "state": {"request": "find records"},
    }


def test_sync_retries_transient_failure_and_keeps_retry_count_header():
    requests = []

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx2.Response(
                503, headers={"retry-after-ms": "0"}, json={"message": "busy"}
            )
        return httpx2.Response(200, json=_answer_body())

    policy = RetryPolicy(
        max_retries=1, backoff_initial=0.001, backoff_max=0.001, backoff_jitter=0
    )
    with TypeSafeClient(
        api_key="key", retry=policy, transport=httpx2.MockTransport(handler)
    ) as client:
        assert client.system_one("find records", _questions()).model == "jev-test"

    assert len(requests) == 2
    assert requests[1].headers["x-typesafe-retry-count"] == "1"


def test_sync_authentication_failure_is_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(401, json={"detail": "bad key"})

    with TypeSafeClient(
        api_key="bad", transport=httpx2.MockTransport(handler)
    ) as client:
        with pytest.raises(TypeSafeAuthenticationError, match="bad key"):
            client.system_one("find records", _questions())

    assert len(calls) == 1


async def test_async_system_one_and_context_manager_close_client():
    seen = []

    async def handler(request):
        seen.append(request)
        return httpx2.Response(200, json=_answer_body())

    client = AsyncTypeSafeClient(api_key="key", transport=httpx2.MockTransport(handler))
    async with client:
        response = await client.system_one("find records", _questions())

    assert response.choices["which"].probabilities["search"] == 0.9
    assert seen[0].headers["authorization"] == "Bearer key"
    assert client._http_client.is_closed
