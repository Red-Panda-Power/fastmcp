"""Exercise the temporary Python 3.8 test environment."""

import asyncio
import sys
from pathlib import Path

import pytest
from hypothesis import given, strategies
from inline_snapshot import snapshot
from pytest_examples import EvalExample, find_examples

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


def test_examples_plugin(tmp_path: Path, eval_example: EvalExample) -> None:
    document = tmp_path / "example.md"
    document.write_text("```py\nanswer = 6 * 7\n```\n", encoding="utf-8")
    example = next(iter(find_examples(document)))
    assert eval_example.run(example)["answer"] == 42
