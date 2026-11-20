# Vendored MCP Python SDK

These sources come from [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) tag `v2.3.0`, commit `2118f14f8a19bc158d8a1cf90af58d85d187f849`. They are copied into this repository so the internal Python 3.8 fork can maintain its own compatibility changes. The original MIT license is in `LICENSE` and in each package directory; `UPSTREAM-README.md` is the original SDK readme.

`mcp-types` is being ported and has its own focused tests under `tests/types`. The FastMCP workspace resolves it from this directory. The `mcp` SDK sources are present for the next part of the port but still require Python 3.10 or newer and are not yet connected to the FastMCP workspace.

To set up and run the type-package checks with UV from the repository root:

```bash
uvx uv@0.13.9 sync --project vendor/python-sdk --python 3.8
uvx uv@0.13.9 run --project vendor/python-sdk --python 3.8 pytest -c vendor/python-sdk/pyproject.toml --noconftest vendor/python-sdk/tests/types
```

The test project's development group contains pytest and snapshot tools. `uv sync --project vendor/python-sdk --no-dev` selects only the type package and its runtime dependencies.
