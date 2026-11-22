"""CLI command binding exercised with Python 3.8-compatible annotations."""

from __future__ import annotations

from fastmcp.cli.cli import app
from fastmcp.cli.install.shared import process_common_args


def test_cli_binds_run_options_with_postponed_annotations() -> None:
    parsed = app.parse_args(
        [
            "run",
            "server.py",
            "--transport",
            "http",
            "--port",
            "9000",
            "--with",
            "internal-package",
        ],
        exit_on_error=False,
        print_error=False,
    )
    command, bound = parsed[:2]

    assert callable(command)
    assert bound.arguments["server_spec"] == "server.py"
    assert bound.arguments["transport"] == "http"
    assert bound.arguments["port"] == 9000
    assert bound.arguments["with_packages"] == ["internal-package"]


def test_cli_binds_cimd_input_validation_parameters() -> None:
    parsed = app.parse_args(
        [
            "auth",
            "cimd",
            "create",
            "--name",
            "Internal client",
            "--redirect-uri",
            "http://localhost:3000/callback",
            "--client-id",
            "https://intranet.example/client.json",
        ],
        exit_on_error=False,
        print_error=False,
    )
    command, bound = parsed[:2]

    assert callable(command)
    assert bound.arguments == {
        "name": "Internal client",
        "redirect_uri": ["http://localhost:3000/callback"],
        "client_id": "https://intranet.example/client.json",
    }


async def test_install_env_file_keeps_command_line_precedence(tmp_path) -> None:
    server = tmp_path / "server.py"
    server.write_text("# internal server", encoding="utf-8")
    env_file = tmp_path / "settings.env"
    env_file.write_text("FROM_FILE=value\nSHARED=old\n", encoding="utf-8")

    result = await process_common_args(
        str(server), "Example", None, ["SHARED=new"], env_file
    )

    assert result[-1] == {"FROM_FILE": "value", "SHARED": "new"}
