import asyncio
import sys

if sys.implementation.name == "cpython":
    if sys.version_info < (3, 11):
        from async_timeout import timeout as async_timeout
    else:
        from asyncio import timeout as async_timeout

elif sys.implementation.name == "circuitpython":
    # This code is preparing the bleak to be compatible with `circuitpython>=9`

    if sys.implementation.version <= (9,):
        raise NotImplementedError("Bleak does not support CircuitPython < 9")
    else:

        class _AsyncTimeout:
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

        async_timeout = _AsyncTimeout

elif sys.implementation.name == "pypy":
    raise NotImplementedError("Unsupported Python implementation: pypy")

else:
    # can't use on pypy for example
    raise NotImplementedError(
        f"Unsupported Python implementation: {sys.implementation.name}"
    )

assert async_timeout  # Ensure we have async_timeout defined
