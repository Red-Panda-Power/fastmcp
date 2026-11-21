# Vendored Monty sandbox

This directory contains the Python client and Rust source needed to build the
Monty 1.1.0 sandbox for the internal FastMCP Python 3.8 migration. The sources
come from [pydantic/monty](https://github.com/pydantic/monty), tag `v1.1.0`,
commit `591527397445bf734873252d1ee20c1b6308fe7f`. The upstream MIT license is
preserved in `LICENSE`; the bundled typeshed sources retain their license and
source commit in `crates/monty-typeshed/vendor/typeshed`.

The Python compatibility helper in `pydantic_monty/_dataclasses.py` is adapted
from this repository's vendored MCP SDK. Its Apache 2.0 license is preserved as
`LICENSE-MCP`. The Python code and the Rust type conversion layer have been
adapted for Python 3.8 without weakening sandbox restrictions or resource limits.

Building the client and worker from source requires Rust 1.96 or newer, Cargo,
and a platform C/C++ toolchain. The isolated UV project installs runtime
dependencies by default and adds pytest and its plugins in the `dev` group:

```bash
uv sync --project vendor/monty --python 3.8
uv run --project vendor/monty --python 3.8 pytest
uv sync --project vendor/monty --python 3.8 --no-dev
```

The root UV project selects this copy for the code-mode extra on Python 3.8.
On Windows, the Python 3.8 client and worker have been built from these sources,
and the isolated development and runtime-only installs have been exercised.
The full FastMCP project does not yet support Python 3.8 installations. Other
deployment platforms still need native builds and runtime tests. Monty's
optional OpenTelemetry extra still needs a Python 3.8 compatibility audit.
