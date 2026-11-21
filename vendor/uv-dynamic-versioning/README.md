# Vendored uv-dynamic-versioning

These sources and tests come from [ninoseki/uv-dynamic-versioning](https://github.com/ninoseki/uv-dynamic-versioning), tag `v0.12.0`, commit `b188c8f1426f9172488973b2091b46366f601ad2`. The original MIT license and README are preserved in `LICENSE` and `UPSTREAM-README.md`.

This copy backports the Hatch version and dependency metadata hooks to Python 3.8. Its UV development project includes the upstream tests, which create their Git repository under pytest's temporary directory to avoid changing the FastMCP repository. The root UV configuration selects this source when building with Python 3.8.
