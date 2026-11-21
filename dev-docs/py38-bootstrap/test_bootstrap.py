"""Exercise the temporary Python 3.8 test environment."""

import asyncio
import sys

import pytest
from hypothesis import given, strategies
from inline_snapshot import snapshot

_retry_attempts = 0


@pytest.mark.asyncio
async def test_python_and_async_plugin() -> None:
    await asyncio.sleep(0)
    assert sys.version_info[:2] == (3, 8)


@given(strategies.integers())
def test_hypothesis_and_snapshot(value: int) -> None:
    assert value - value == snapshot(0)


@pytest.mark.flaky(retries=1)
def test_retry_plugin() -> None:
    global _retry_attempts
    _retry_attempts += 1
    assert _retry_attempts == 2
