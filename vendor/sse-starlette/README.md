# Vendored SSE transport

This is [sse-starlette](https://github.com/sysid/sse-starlette) version 3.7.0,
tag `v3.7.0`, commit `e023a93774b100ccd614aedb1251f60d70b6ec29`. The
upstream BSD license and authors are included. Its dependencies are adapted to
the Python 3.8-compatible AnyIO and Starlette releases; the original source is
tested against them in this UV project and by the vendored MCP SDK.

The newer upstream implementation isolates SSE shutdown state per thread. The
last published Python 3.8 version shares an event across loops and fails when
servers are started on different event loops in one process.
