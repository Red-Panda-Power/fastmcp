# Vendored py-key-value-aio

These sources and selected upstream tests come from [strawgate/py-key-value](https://github.com/strawgate/py-key-value), tag `0.4.6`, commit `8b7ff8fa0a082a6cf7256384f8eddacfdd8b3f74`. They are being backported for the internal FastMCP Python 3.8 fork. The upstream Apache 2.0 license and README are preserved as `LICENSE` and `UPSTREAM-README.md`.

The port and its UV project are still being validated. The root FastMCP workspace continues to use the published package. Runtime backends are optional extras; the development group contains only test and development tooling plus the integrations exercised by the local suite. Deployment installations can therefore omit it.

## Python 3.8 backend matrix

The following extras resolve for CPython 3.8 on Windows and Linux: `aerospike`,
`azure-tables`, `duckdb`, `dynamodb`, `elasticsearch`, `firestore`,
`memcached`, `mongodb`, `opensearch`, `postgresql`, `rocksdb`, `s3`, and
`vault`. They remain optional because several require a running database or
cloud service. The `registry` extra has no third-party dependency and is
Windows-only because it uses `winreg`.

chDB 3.7.2 is available as a CPython 3.8 `abi3` wheel on Linux (including
manylinux and musllinux), while chDB 4.1.1+ requires Python 3.9. It has no
Windows CPython 3.8 wheel, so that backend remains unavailable on Windows
unless an internal native backport is supplied.

Valkey GLIDE 2.1+ requires Python 3.9 and has no CPython 3.8 Windows wheel.
On Python 3.8 the `valkey` extra instead installs the Redis-protocol client and
keeps `ValkeyStore(host=..., port=..., db=..., username=..., password=...)`
and supplied `redis.asyncio.Redis` clients working with Valkey. GLIDE cluster
clients and GLIDE configuration objects remain a Python 3.9+ capability; the
store raises a clear `ValueError` if one is requested on Python 3.8.

The matrix is resolver-verified against CPython 3.8 for Windows and Linux. It
does not replace integration testing against a real backend service; credentials
and endpoint validation continue to be handled by each store implementation.

Aerospike is an exception to the Python 3.8 wheel availability story: its
CPython 3.8 dependency is capped below 19 because version 19's build backend
evaluates Python 3.10 syntax. Newer Python versions retain the upstream
unbounded Aerospike range. On Windows, Aerospike 18.x builds from source and
requires MSBuild plus the Aerospike client C dependencies; it has no usable prebuilt
CPython 3.8 wheel. Linux deployments need the corresponding native build
toolchain and client libraries. This is a native integration constraint, not a
reason to bypass authentication or validation in `AerospikeStore`.

DuckDB is capped below 1.3 on CPython 3.8 so Windows receives its 1.2.x wheel
instead of attempting an unsupported source build. This cap is not needed by
newer Python interpreters in the upstream project, but it is necessary for the
shared Python 3.8-compatible package metadata used by this fork.
