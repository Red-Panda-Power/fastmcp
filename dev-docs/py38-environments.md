# Python 3.8 environments

The root UV project supports the internal Python 3.8 deployment and the
existing Python 3.11+ line. Python 3.9 and 3.10 are intentionally excluded
until they receive their own compatibility audit.

Create the normal Python 3.8 development environment with its test tools:

```powershell
uv sync --locked --python 3.8
```

The default `dev` group includes pytest, static-check tools, the OpenAI and
Anthropic integrations, and the regular FastMCP development dependencies. It
does not build the optional native code-mode sandbox on Python 3.8.

Run a focused set of Python 3.8 tests with:

```powershell
uv run --locked --python 3.8 pytest -n 0 tests/test_py38_server_compat.py tests/test_py38_app_provider.py tests/utilities/test_asgi_transport.py tests/client/sampling/handlers/test_anthropic_handler.py tests/client/sampling/handlers/test_openai_handler.py
```

The complete upstream test suite has not yet been ported: tests for deferred
Tasks, MCP Apps UI, and some maintenance scripts can still fail during
collection on Python 3.8. Select the tests relevant to the change being made.

The repository-wide `ty` hook also checks upstream code for the deferred
integrations. Run the complete static checks in a separate Python 3.12
development environment so those dependencies are available:

```powershell
$env:UV_PROJECT_ENVIRONMENT = ".venv/fastmcp312"
$env:UV_PYTHON = "3.12"
uv sync --locked --python 3.12
uv run --locked prek -c .pre-commit-config.yaml run --all-files
Remove-Item Env:UV_PROJECT_ENVIRONMENT, Env:UV_PYTHON
```

To install the native code-mode sandbox:

```powershell
uv sync --locked --python 3.8 --group dev-code-mode
```

The sandbox's Monty client and runtime are built from the vendored sources.
Their Windows build is memory-intensive, so run it with sufficient available
memory and limited concurrent builds when necessary.

Deployment environments should omit the development group:

```powershell
uv sync --locked --python 3.8 --no-dev
```

FastAPI is optional at runtime. Internal deployments that expose FastMCP tools
through a FastAPI application can install it without test dependencies:

```powershell
uv sync --locked --python 3.8 --no-dev --extra fastapi
```

This resolves FastAPI 0.124.4 on Python 3.8, with Starlette 0.44.0 and
Pydantic 2.10.6. Python 3.11+ continues to use the existing FastAPI minimum.

MCP Apps UI, Azure Identity, and Gemini are not included for Python 3.8.
Tasks are deferred across this internal migration branch: its source remains
in `fastmcp_tasks/`, but its extra and default development installation will
be restored only after its dynamic-versioned packaging can be locked reliably.
