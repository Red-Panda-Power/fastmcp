import asyncio
import logging

import httpx
import pytest
from starlette.applications import Starlette
from starlette.routing import Route

from sse_starlette.sse import EventSourceResponse


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def httpx_client():
    async def endless(request):
        async def events():
            count = 0
            try:
                while True:
                    count += 1
                    yield {"data": count}
                    await asyncio.sleep(0.3)
            except asyncio.CancelledError:
                logging.getLogger(__name__).info("Disconnected from client")
                raise

        return EventSourceResponse(events())

    app = Starlette(routes=[Route("/endless", endless)])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        yield client


@pytest.fixture(autouse=True)
def reset_shutdown_state():
    from sse_starlette.sse import AppStatus, _thread_state

    AppStatus.should_exit = False
    AppStatus.enable_automatic_graceful_drain = True
    if hasattr(_thread_state, "shutdown_state"):
        del _thread_state.shutdown_state
    yield
    AppStatus.should_exit = True
    AppStatus.enable_automatic_graceful_drain = True
    if hasattr(_thread_state, "shutdown_state"):
        del _thread_state.shutdown_state
