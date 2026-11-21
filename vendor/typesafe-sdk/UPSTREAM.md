# TypeSafe SDK provenance

This directory vendors TypeSafe AI's Python SDK version 0.5.7, imported from
[`typesafe-ai/typesafe-sdk-python` tag `v0.5.7`](https://github.com/typesafe-ai/typesafe-sdk-python/tree/v0.5.7)
at commit `f307bce731f6de17a3d9267311c20d699ae17694`.

The upstream project is MIT licensed. Its unmodified license is retained in
[`LICENSE`](LICENSE). The Python 3.8 changes in this fork are deliberately
limited to dependency metadata and runtime-compatible typing expressions;
request construction, authentication, retry behavior, error translation, and
the synchronous and asynchronous client APIs remain upstream behavior.

The original upstream test suite remains under `tests/` for reference, but
uses Python 3.10-only test annotations. `compat_tests/` is the executable
Python 3.8 regression suite for this vendor package.
