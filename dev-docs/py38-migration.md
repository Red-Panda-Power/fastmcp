# Python 3.8 migration baseline

This internal fork targets Python 3.8 while preserving the current FastMCP features, except that MCP Apps UI and `prefab-ui` may be omitted. Prefect Horizon account and deployment integration is removed from this fork; general server deployment and authentication remain supported. The Python 3.8 environment is a starting point, not a working installation of FastMCP. The main workspace still declares Python 3.11 or newer and its existing lockfile does not support Python 3.8.

Removing the Horizon commands does not revoke existing Horizon API keys or delete their local state. Earlier versions stored the key in `FASTMCP_HOME/cli/auth.json` and the selected host in `FASTMCP_HOME/cli/config.json`. Revoke any unused key through Horizon and remove those files if they are no longer needed. Other FastMCP authentication state is separate.

The MCP SDK and protocol type sources from upstream version 2.3.0 are vendored under `vendor/python-sdk`. The local `mcp-types` package is selected by the root UV project. The SDK's separate UV project now resolves and imports on Python 3.8, and tests cover client/server protocol calls, HTTP transport, authentication, and custom validation on Python 3.8 and 3.12. The SDK port is still being audited, and the root project still resolves the published SDK.

HTTPX2 and HTTPCore2 2.12.0 are vendored under `vendor/httpx2` and are used by the vendored SDK's development project. Their isolated UV project tests the backport on Python 3.8 and 3.12, including HTTP/1.1, HTTP/2, SOCKS, TLS verification, WebSockets, cancellation, SSE and content decoding. On Python 3.8, the default TLS context uses the standard library because `truststore` requires Python 3.10; certificate and hostname verification remain enabled. The root FastMCP workspace still resolves the published HTTP transport until the SDK port is ready.

The SDK's Python 3.8 dependency set also uses local backports of `typing-inspection` 0.4.2 and `sse-starlette` 3.7.0. The SDK's runtime-only UV installation excludes pytest and Trio, while its development environment includes them for the test suite. These checks do not establish that the FastMCP workspace itself can yet be installed on Python 3.8.

`uncalled-for` 0.6.1, the dependency injection engine, is vendored under `vendor/uncalled-for`. Its upstream tests run on Python 3.8 and 3.12, and the FastMCP dependency and shared-context tests pass with this copy on Python 3.12. The root project has not yet switched to this copy; its Python 3.8 integration remains to be verified as part of the workspace port.

`py-key-value-aio` 0.4.6 is being backported under `vendor/py-key-value`. Its in-memory, file-tree, Pydantic, encryption, size-limit, and statistics paths have focused Python 3.8 tests; Redis and keyring are also exercised against test doubles. The package still needs its other backend extras audited and restored, and the root project continues to use the published package.

The `prefab-ui` dependency is now restricted to Python 3.10 and newer; MCP Apps UI is unavailable on Python 3.8. The dependency audit below records the original constraints before this change.

## Dependency audit

UV resolution against CPython 3.8.20 found no compatible published releases of these dependencies used by the current project:

| Dependency | Existing purpose |
| --- | --- |
| `mcp`, `mcp-types` | MCP protocol, transports, and models |
| `httpx2` | HTTP client used by FastMCP and the MCP SDK |
| `uncalled-for` | Dependency injection |
| `py-key-value-aio` | Client and server storage |
| `pydocket` | Background tasks |
| `prefab-ui` | Optional MCP Apps UI; this fork may omit it |
| `pydantic-monty` | Code mode; no compatible Python 3.8 wheel was found |
| `pytest-retry` | Development test retry plugin |

Supporting the remaining features will require compatible backports or alternatives that preserve the required APIs and behavior. Simply lowering `requires-python` or dependency minimums cannot make these packages installable. Native dependencies, including code mode, also need a viable Python 3.8 build and platform verification.

### FastAPI

FastAPI is currently declared in the root development group as `fastapi>=0.115.12`. On Windows with Python 3.8.20 and Pydantic 2.10.6, UV resolved FastAPI 0.124.4, Starlette 0.44.0, AnyIO 4.5.2, and HTTPX 0.28.1. The vendored type package's development tests exercise this combination through FastAPI's in-process HTTP client. The root FastMCP dependency currently requires `starlette>=1.0.1`, so that constraint also needs to change or be backported before the full Python 3.8 environment can resolve. Recheck the combination on the intended deployment platform.

The published `uv-dynamic-versioning` build plugin has no installable non-yanked Python 3.8 release. A Python 3.8 backport of version 0.12.0 is vendored under `vendor/uv-dynamic-versioning` and selected by the root UV configuration for builds using Python 3.8. UV has built all four workspace wheels with that interpreter and verified dynamic version and dependency metadata. Those wheels still declare Python 3.11 or newer and are not Python 3.8 installations; the dependency and source migration remains necessary.

An independent `uv pip install --dry-run --no-deps` check on Windows tested 68 direct requirement strings from the root and workspace projects, including optional and development groups. Thirty of those constraints had no Python 3.8-compatible candidate:

- Core and shared runtime: `authlib`, `cyclopts`, `griffelib`, `httpx2`, `joserfc`, `mcp`, `mcp-types`, `openapi-pydantic`, `opentelemetry-api`, `py-key-value-aio`, `pydantic`, `python-dotenv`, `python-multipart`, `starlette`, `uncalled-for`, `uvicorn`, `watchfiles`, and `websockets`.
- Optional integrations and tasks: `PyJWT`, `google-genai`, `prefab-ui`, `pydantic-monty`, `pydocket`, and `typesafe-sdk`.
- Build: `uv-dynamic-versioning`.
- Development: `hypothesis`, `opentelemetry-exporter-otlp-proto-grpc`, `pytest-asyncio`, `pytest-cov`, and `pytest-retry`.

This check used the current declared constraints; it does not imply that every listed package lacks an older compatible release, nor that packages with a candidate work together or import successfully. Transitive dependencies, build dependencies beyond the declared requirements, and other target platforms still need review.

For example, the current `pydantic>=2.12.0` constraint is incompatible with Python 3.8; UV resolved `pydantic==2.10.6` when that minimum was removed. Its API and behavior must be checked against the project and backported dependencies before changing the project requirement.

## Source audit

An initial syntax scan with CPython 3.8.20 found 10 of 277 `fastmcp_slim/fastmcp` Python files and 20 of 576 test files fail to parse. Another 48 parsable slim files and two task files import names unavailable from the Python 3.8 `typing` module. A scan of the published `mcp==2.3.0` wheel also found eight of its 124 Python files fail to parse, and one of 11 files in `uncalled-for==0.6.2` fails to parse. Parsing alone does not check runtime evaluation of annotations, standard-library API changes, or dependency compatibility.

## Temporary test tooling

`py38-bootstrap` is a separate UV project containing Python 3.8 test tools. It does not install FastMCP or its runtime dependencies. The bootstrap installs local Python 3.8 backports of `pytest-retry` 1.7.0 and `pytest-examples` 0.0.18. It is only for migration work; the normal root development dependency group must eventually provide the complete test environment. Deployment installs should not use this group.

After the runtime and dependency ports, validate the root UV lockfile and both runtime-only and development installations on Python 3.8, then exercise the affected protocol, feature, and optional-integration paths. Do not advertise full Python 3.8 support until those checks pass.
