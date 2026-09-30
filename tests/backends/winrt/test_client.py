"""Tests for the WinRT client's async-operation plumbing."""

import asyncio
import sys
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional, cast

import pytest

if TYPE_CHECKING:
    if sys.platform != "win32":
        assert False, "This backend is only available on Windows"

if sys.platform != "win32":
    pytest.skip("skipping windows-only tests", allow_module_level=True)

from winrt.windows.foundation import AsyncStatus

from bleak.backends.winrt.client import FutureLike

if TYPE_CHECKING:
    from winrt.windows.foundation import IAsyncOperation


class FakeAsyncOperation:
    """
    The parts of IAsyncOperation that FutureLike uses.

    Like the real thing, the status can already read COMPLETED before the
    completed handler has been invoked: WinRT flips the status first and
    calls the handler afterwards, on its own thread.
    """

    def __init__(self, result: str, status: AsyncStatus = AsyncStatus.STARTED):
        self.status = status
        self.completed: Optional[Callable[[FakeAsyncOperation, AsyncStatus], None]]
        self.completed = None
        self._result = result
        self.results_read_on: list[str] = []

    def complete(self) -> None:
        """Complete the way WinRT does: status first, then the handler."""
        self.status = AsyncStatus.COMPLETED
        assert self.completed is not None
        self.completed(self, AsyncStatus.COMPLETED)

    def get_results(self) -> str:
        self.results_read_on.append(threading.current_thread().name)
        return self._result

    def cancel(self) -> None:
        self.status = AsyncStatus.CANCELED


def future_of(op: FakeAsyncOperation) -> FutureLike[str]:
    return FutureLike(cast("IAsyncOperation[str]", op))


async def test_future_like_returns_result() -> None:
    op = FakeAsyncOperation("value")
    future = future_of(op)
    op.complete()
    assert await future == "value"


async def test_future_like_waits_for_the_handler_of_a_fast_operation() -> None:
    """
    An operation that completed before it was awaited, but whose handler has
    not run yet, must still be waited for. Reading the status alone here
    used to make ``await`` return at once with no result stored (an
    AssertionError on CI from cached GATT discovery on a fast reconnect).
    """
    op = FakeAsyncOperation("value", status=AsyncStatus.COMPLETED)
    future = future_of(op)
    assert not future.done()

    # The handler arrives from another thread a little later, as it does
    # when WinRT completes on its thread pool.
    loop = asyncio.get_running_loop()
    deliver_thread_name: list[str] = []

    def deliver() -> None:
        deliver_thread_name.append(threading.current_thread().name)
        assert op.completed is not None
        op.completed(op, AsyncStatus.COMPLETED)

    loop.call_later(0.05, lambda: threading.Thread(target=deliver).start())

    assert await future == "value"
    assert future.done()
    # The result is read on the delivering thread, not the loop's.
    assert op.results_read_on == deliver_thread_name


async def test_future_like_result_before_handler_is_invalid_state() -> None:
    op = FakeAsyncOperation("value", status=AsyncStatus.COMPLETED)
    future = future_of(op)
    with pytest.raises(asyncio.InvalidStateError):
        future.result()
