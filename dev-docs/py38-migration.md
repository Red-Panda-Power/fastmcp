# Python 3.8 migration baseline

This internal fork targets Python 3.8 while preserving the current FastMCP features, except that MCP Apps UI and `prefab-ui` may be omitted. The Python 3.8 environment is a starting point, not a working installation of FastMCP. The main workspace still declares Python 3.11 or newer and its existing lockfile does not support Python 3.8.

The MCP SDK and protocol type sources from upstream version 2.3.0 are now vendored under `vendor/python-sdk`. The local `mcp-types` package is selected by the root UV project and has focused Python 3.8 tests. The copied `mcp` SDK itself is still being ported and the root project still resolves the published SDK.

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

The current `uv-dynamic-versioning` build backend also has no installable non-yanked Python 3.8 release, so the workspace build process needs a compatible replacement or backport.

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

`py38-bootstrap` is a separate UV project containing Python 3.8 test tools. It does not install FastMCP or its runtime dependencies. It omits `pytest-retry` because no published release supports Python 3.8, and `pytest-examples` because the tested 0.0.16 and 0.0.18 releases fail to import on Python 3.8 despite their package metadata. It is only for migration work; the normal root development dependency group must eventually provide the complete test environment. Deployment installs should not use this group.

After the runtime and dependency ports, validate the root UV lockfile and both runtime-only and development installations on Python 3.8, then exercise the affected protocol, feature, and optional-integration paths. Do not advertise full Python 3.8 support until those checks pass.
