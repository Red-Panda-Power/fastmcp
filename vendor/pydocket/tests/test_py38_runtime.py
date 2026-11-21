"""Runtime coverage for the Python 3.8 compatibility layer.

These tests deliberately avoid the upstream conftest so they can run against
the Python 3.8 test environment, whose pytest-asyncio release predates some
of the upstream test configuration options.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from docket import Docket, ExecutionState, Progress, Worker
from docket._cancellation import cancel_task
from docket.dependencies import CurrentDocket, CurrentWorker, Depends


async def test_memory_worker_executes_and_finishes() -> None:
    values = []

    async def record(value: str) -> str:
        values.append(value)
        return value

    async with Docket(name="py38-runtime", url="memory://") as docket:
        docket.register(record)
        execution = await docket.add(record)("executed")

        async with Worker(docket, concurrency=1) as worker:
            await worker.run_until_finished()

        assert execution.key
        assert values == ["executed"]
        assert (await docket.snapshot()).total_tasks == 0


async def test_cancel_task_supports_python_38_task_cancel() -> None:
    task = asyncio.create_task(asyncio.Event().wait())
    await asyncio.sleep(0)

    await cancel_task(task, "py38 cleanup")

    assert task.cancelled()


async def test_memory_worker_run_forever_cancels_cleanly() -> None:
    async with Docket(name="py38-cancellation", url="memory://") as docket:
        async with Worker(docket, concurrency=1) as worker:
            run_task = asyncio.create_task(worker.run_forever())
            deadline = asyncio.get_running_loop().time() + 5
            while True:
                session = worker._processing_session  # pyright: ignore[reportPrivateUsage]
                if session is not None and session.cancellation_ready.is_set():
                    break
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError("worker did not become ready")
                await asyncio.sleep(0)

            run_task.cancel()
            _, pending = await asyncio.wait([run_task], timeout=5)
            assert not pending


async def test_worker_context_progress_dependency_and_result() -> None:
    events = []
    observed = {}

    @asynccontextmanager
    async def lifecycle():
        events.append("enter")
        try:
            yield None
        finally:
            events.append("exit")

    async def task(
        value: int,
        progress: Progress = Progress(),
        current_docket: Docket = CurrentDocket(),
        current_worker: Worker = CurrentWorker(),
    ) -> int:
        events.append("task")
        observed["docket"] = current_docket
        observed["worker"] = current_worker
        await progress.set_total(2)
        await progress.increment(2)
        await progress.set_message("done")
        return value * 2

    async with Docket(name="py38-context", url="memory://") as docket:
        docket.register(task)
        execution = await docket.add(task)(21)
        async with Worker(
            docket,
            dependencies={"lifecycle": Depends(lifecycle)},
        ) as worker:
            await worker.run_until_finished()

        assert await execution.get_result() == 42
        assert observed == {"docket": docket, "worker": worker}
        assert events == ["enter", "task", "exit"]


async def test_scheduled_cancellation_and_failed_state() -> None:
    ran = []

    async def scheduled() -> None:
        ran.append("scheduled")

    async def fails() -> None:
        raise ValueError("expected task error")

    async with Docket(name="py38-states", url="memory://") as docket:
        docket.register(scheduled)
        docket.register(fails)
        future = await docket.add(
            scheduled, when=datetime.now(timezone.utc) + timedelta(seconds=30)
        )()
        failed = await docket.add(fails)()
        await docket.cancel(future.key)

        async with Worker(docket, concurrency=1) as worker:
            await worker.run_until_finished()

        await future.sync()
        await failed.sync()
        assert future.state == ExecutionState.CANCELLED
        assert failed.state == ExecutionState.FAILED
        assert ran == []
