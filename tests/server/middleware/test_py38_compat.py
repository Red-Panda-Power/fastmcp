"""Python 3.8 regression coverage for server middleware."""

import pytest

from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.middleware import MiddlewareContext
from fastmcp.server.middleware.ping import PingMiddleware
from fastmcp.server.middleware.rate_limiting import TokenBucketRateLimiter
from fastmcp.server.middleware.timing import TimingMiddleware


def test_middleware_runtime_types_initialize_on_python_38():
    """Deferred annotations and typing backports do not block middleware setup."""

    cache = ResponseCachingMiddleware()
    context = MiddlewareContext(message="request")

    assert context.message == "request"
    assert cache.statistics().list_tools is None
    assert isinstance(ErrorHandlingMiddleware(), ErrorHandlingMiddleware)
    assert isinstance(LoggingMiddleware(), LoggingMiddleware)
    assert isinstance(PingMiddleware(), PingMiddleware)
    assert isinstance(TimingMiddleware(), TimingMiddleware)


@pytest.mark.asyncio
async def test_token_bucket_rate_limiting_still_enforces_capacity():
    """Runtime compatibility leaves rate-limit behavior unchanged."""

    limiter = TokenBucketRateLimiter(capacity=1, refill_rate=0)

    assert await limiter.consume()
    assert not await limiter.consume()
