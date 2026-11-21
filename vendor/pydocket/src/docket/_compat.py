"""Small runtime compatibility surface for supported Python versions."""

from __future__ import annotations

import asyncio

try:
    from asyncio import TaskGroup
except ImportError:  # Python 3.8-3.10

    class TaskGroup:
        """Structured task scope compatible with Python 3.8 cancellation."""

        def __init__(self) -> None:
            self._tasks = set()

        async def __aenter__(self):
            return self

        def create_task(self, coroutine, *, name=None):
            task = asyncio.create_task(coroutine, name=name)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return task

        async def __aexit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                self._cancel()
            try:
                results = await asyncio.gather(*self._tasks, return_exceptions=True)
            except asyncio.CancelledError:
                self._cancel()
                await asyncio.gather(*self._tasks, return_exceptions=True)
                raise

            errors = [
                result
                for result in results
                if isinstance(result, BaseException)
                and not isinstance(result, asyncio.CancelledError)
            ]
            if exc_type is None and errors:
                raise ExceptionGroup("unhandled errors in a TaskGroup", errors)
            return False

        def _cancel(self) -> None:
            for task in self._tasks:
                if not task.done():
                    task.cancel()


try:
    from builtins import BaseExceptionGroup, ExceptionGroup
except ImportError:  # Python 3.8-3.10
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup

__all__ = ["BaseExceptionGroup", "ExceptionGroup", "TaskGroup"]
