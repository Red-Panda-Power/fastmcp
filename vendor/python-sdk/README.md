# Vendored MCP Python SDK

These sources come from [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) tag `v2.3.0`, commit `2118f14f8a19bc158d8a1cf90af58d85d187f849`. They are copied into this repository so the internal Python 3.8 fork can maintain its own compatibility changes. The original MIT license is in `LICENSE` and in each package directory; `UPSTREAM-README.md` is the original SDK readme.

`mcp-types` has focused compatibility tests under `tests/types`, and the FastMCP workspace resolves it from this directory. The `mcp` SDK has a separate UV project, local Python 3.8-compatible dependencies, and tests for protocol calls, HTTP transport, and authentication. Its migration remains in progress, and the root FastMCP workspace still resolves the published SDK.

To set up and run the type-package checks with UV from the repository root:

```bash
uv sync --project vendor/python-sdk --python 3.8
uv run --project vendor/python-sdk --python 3.8 pytest -c vendor/python-sdk/pyproject.toml --noconftest vendor/python-sdk/tests/types
```

The test project's development group contains pytest and snapshot tools. `uv sync --project vendor/python-sdk --no-dev` selects only the type package and its runtime dependencies.

For the SDK itself, use `uv sync --project vendor/python-sdk/mcp --python 3.8` and run `pytest --noconftest vendor/python-sdk/tests/compat` in that environment. Add `--no-dev` when installing the SDK without test tools. The SDK project uses local backports of its HTTP transport, SSE transport, and typing inspection dependency on Python 3.8.
