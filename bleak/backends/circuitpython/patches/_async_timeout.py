import asyncio
import sys


class AsyncTimeout:
    def __init__(self, timeout):
        if sys.implementation.name != "circuitpython":
            print(
                "Warning: This timeout manager is for CircuitPython. "
                "Use the native `asyncio.timeout` on standard Python."
            )
        self.timeout = timeout
        self._task = None

    async def __aenter__(self):
        self._task = asyncio.create_task(asyncio.sleep(self.timeout))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if exc_type is asyncio.CancelledError and self._task.done():
            if self._task.cancelled():
                raise asyncio.TimeoutError("Operation timed out") from exc_val

        # If any other exception occurred, let it propagate.
        return False


async_timeout = AsyncTimeout
