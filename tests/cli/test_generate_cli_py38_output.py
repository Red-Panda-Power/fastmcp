"""Generated CLI scripts must remain executable on Python 3.8."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import mcp_types

from fastmcp.cli.generate import generate_cli_script


def _generate_script(path: Path) -> None:
    tool = mcp_types.Tool(
        name="echo",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        },
    )
    path.write_text(
        generate_cli_script(
            server_name="Generated",
            server_spec="http://unused.example/mcp",
            transport_code=repr("http://unused.example/mcp"),
            extra_imports=set(),
            tools=[tool],
        ),
        encoding="utf-8",
    )


def test_generated_cli_runs_help_and_binds_modern_annotations(tmp_path: Path) -> None:
    script_path = tmp_path / "generated_cli.py"
    _generate_script(script_path)

    help_result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0, help_result.stderr
    assert "call-tool" in help_result.stdout

    parse_program = f"""
import runpy

namespace = runpy.run_path({str(script_path)!r}, run_name='generated_cli')
parsed = namespace['app'].parse_args(
    ['call-tool', 'echo', '--name', 'Ada', '--tags', 'one'],
    exit_on_error=False,
    print_error=False,
)
bound = parsed[:2][1]
assert bound.arguments['name'] == 'Ada'
assert bound.arguments['tags'] == ['one']
"""
    parse_result = subprocess.run(
        [sys.executable, "-c", parse_program],
        capture_output=True,
        text=True,
        check=False,
    )
    assert parse_result.returncode == 0, parse_result.stderr
