"""Horizon device authorization workflow."""

# ruff: noqa: UP045

from __future__ import annotations

import asyncio
import time
import webbrowser
from contextlib import suppress
from typing import Awaitable, Callable, Optional

from pydantic import SecretStr

from fastmcp.cli.deploy.horizon_client import (
    DeviceAuthorization,
    DeviceMetadata,
    HorizonClient,
)


class DeviceAuthorizationError(RuntimeError):
    """Device authorization did not complete."""


class DeviceAuthorizationDeniedError(DeviceAuthorizationError):
    """The user denied the device authorization request."""


class DeviceAuthorizationExpiredError(DeviceAuthorizationError):
    """The device authorization request expired."""


async def poll_device_authorization(
    client: HorizonClient,
    authorization: DeviceAuthorization,
    *,
    sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> SecretStr:
    """Poll at the server interval until the device request completes."""
    sleep = asyncio.sleep if sleep is None else sleep
    deadline = monotonic() + authorization.expires_in
    interval = float(authorization.interval)

    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise DeviceAuthorizationExpiredError(
                "The device authorization request expired"
            )

        await sleep(min(interval, remaining))
        if monotonic() >= deadline:
            raise DeviceAuthorizationExpiredError(
                "The device authorization request expired"
            )

        result = await client.exchange_device_authorization(authorization.device_code)
        if result.access_token is not None:
            return result.access_token
        if result.error == "authorization_pending":
            continue
        if result.error == "slow_down":
            interval += 5
            continue
        if result.error == "access_denied":
            raise DeviceAuthorizationDeniedError(
                "The device authorization request was denied"
            )
        if result.error == "expired_token":
            raise DeviceAuthorizationExpiredError(
                "The device authorization request expired"
            )

        raise DeviceAuthorizationError("Device authorization failed")


async def authorize_device(
    client: HorizonClient,
    *,
    metadata: Optional[DeviceMetadata] = None,
    on_challenge: Optional[Callable[[DeviceAuthorization], None]] = None,
    open_browser: bool = False,
    browser_opener: Callable[[str], object] = webbrowser.open,
    sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> SecretStr:
    """Create, present, and complete a Horizon device authorization."""
    authorization = await client.create_device_authorization(metadata)
    if on_challenge is not None:
        on_challenge(authorization)

    if open_browser:
        with suppress(OSError, webbrowser.Error):
            browser_opener(authorization.verification_uri_complete)

    return await poll_device_authorization(
        client,
        authorization,
        sleep=sleep,
        monotonic=monotonic,
    )
