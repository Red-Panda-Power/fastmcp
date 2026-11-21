# Vendored HTTP transport

This directory contains HTTPX2 and HTTPCore2 2.12.0 from
<https://github.com/pydantic/httpx2>, tag `v2.12.0`, commit
`71ae23be5448f859c2b4e21d9972ddfa7b8d759d`. The upstream BSD licenses are
included. Changes here support Python 3.8 for FastMCP's internal deployment.

Python 3.8 uses the standard library's default TLS trust store because the
`truststore` package requires Python 3.10. Certificate and hostname verification
remain enabled by default. Newer Python versions continue to use `truststore`.

The isolated UV project installs the vendored packages with HTTP/2, WebSocket,
SOCKS, Brotli and Zstandard support. Its development group contains the test
tools. The tests include selected upstream HTTPX2/HTTPCore2 tests plus local
HTTPS, WebSocket, and compatibility checks. Run them with:

```sh
uv sync --project vendor/httpx2 --python 3.8
uv run --project vendor/httpx2 --python 3.8 pytest -c vendor/httpx2/pyproject.toml --noconftest vendor/httpx2/tests
```

The vendored MCP SDK's test project uses these packages; the main FastMCP
workspace still uses the published HTTP transport while the port is in progress.
