# Vendored py-key-value-aio

These sources and selected upstream tests come from [strawgate/py-key-value](https://github.com/strawgate/py-key-value), tag `0.4.6`, commit `8b7ff8fa0a082a6cf7256384f8eddacfdd8b3f74`. They are being backported for the internal FastMCP Python 3.8 fork. The upstream Apache 2.0 license and README are preserved as `LICENSE` and `UPSTREAM-README.md`.

The port and its UV project are still being validated. The root FastMCP workspace continues to use the published package. The development group includes test tools and the in-memory, file-tree, disk, Redis, keyring, Pydantic, and encryption integrations used or documented by FastMCP; deployment installations can omit the development group. Other upstream backend extras are not yet included in this project's dependency metadata and still need a Python 3.8 compatibility audit.
