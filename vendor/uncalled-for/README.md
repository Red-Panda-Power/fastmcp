# Vendored uncalled-for

The sources and tests in this directory come from [uncalled-for](https://github.com/chrisguidry/uncalled-for) tag `0.6.1`, commit `eb1e0292fb3f74fc10693df1aeb9d0f1481daaba`. They are maintained here for the internal FastMCP Python 3.8 port. The upstream MIT license and README are preserved as `LICENSE` and `UPSTREAM-README.md`.

This package has a separate UV project for compatibility work. Install its development dependencies with `uvx uv@0.13.9 sync --project vendor/uncalled-for --python 3.8`, and run its tests with that environment's `python -m pytest -c vendor/uncalled-for/pyproject.toml vendor/uncalled-for/tests`. A deployment can omit development tools with `--no-dev`. The FastMCP workspace still resolves the published dependency until its own Python 3.8 dependency constraints are ready.
