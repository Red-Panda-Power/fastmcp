"""Regression coverage for forwarding server arguments with Cyclopts 2."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cyclopts.exceptions import UnknownOptionError

import fastmcp.cli.cli as cli_module
from fastmcp.cli import app


@pytest.mark.parametrize(
    ("tokens", "expected_args"),
    [
        (
            ["run", "server.py", "--", "--config", "test.json", "--debug"],
            ("server.py", "--config", "test.json", "--debug"),
        ),
        (
            [
                "run",
                "server.py",
                "--transport",
                "http",
                "--port",
                "8080",
                "--",
                "--server-port",
                "9000",
            ],
            ("server.py", "--server-port", "9000"),
        ),
        (["run", "server.py", "--", "--"], ("server.py", "--")),
    ],
)
def test_run_server_args_after_separator_are_bound(
    tokens: list[str], expected_args: tuple[str, ...]
) -> None:
    """The separator belongs to the CLI, while all following args reach the server."""
    command, bound = app.parse_args(
        tokens,
        exit_on_error=False,
        print_error=False,
    )[:2]

    assert command is cli_module.run
    assert bound.args == expected_args


def test_run_server_args_after_separator_do_not_bind_fastmcp_options() -> None:
    """FastMCP options after the separator belong to the target server."""
    _, bound = app.parse_args(
        ["run", "server.py", "--", "--port", "1234", "--transport", "http"],
        exit_on_error=False,
        print_error=False,
    )[:2]

    assert bound.args == ("server.py", "--port", "1234", "--transport", "http")
    assert "port" not in bound.arguments
    assert "transport" not in bound.arguments


def test_run_server_args_before_separator_reject_unknown_options() -> None:
    """The compatibility path does not relax FastMCP option validation."""
    with pytest.raises(UnknownOptionError):
        app.parse_args(
            ["run", "server.py", "--unknown"],
            exit_on_error=False,
            print_error=False,
        )


async def test_run_server_args_after_separator_reach_run_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parsed server arguments reach the direct run path unchanged."""
    config = SimpleNamespace(
        deployment=SimpleNamespace(
            transport="stdio",
            host=None,
            port=None,
            path=None,
            log_level=None,
            args=[],
        ),
        environment=SimpleNamespace(build_command=lambda command: command),
    )
    run_command = AsyncMock()
    monkeypatch.setattr(
        cli_module,
        "load_and_merge_config",
        lambda server_spec, **kwargs: (config, server_spec),
    )
    monkeypatch.setattr(cli_module, "is_already_in_uv_subprocess", lambda: True)
    monkeypatch.setattr(cli_module.run_module, "run_command", run_command)

    command, bound = app.parse_args(
        ["run", "server.py", "--", "--port", "1234", "--transport", "http"],
        exit_on_error=False,
        print_error=False,
    )[:2]
    await command(*bound.args, **bound.kwargs)

    assert run_command.await_args.kwargs["server_args"] == [
        "--port",
        "1234",
        "--transport",
        "http",
    ]
