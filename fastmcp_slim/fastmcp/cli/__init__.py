"""FastMCP CLI package."""

from fastmcp.cli._compat import install_cyclopts_py38_annotation_support

install_cyclopts_py38_annotation_support()

try:
    from .cli import app
except ImportError as exc:
    from fastmcp import _install_hints

    raise ImportError(_install_hints.CLI_SUPPORT) from exc
