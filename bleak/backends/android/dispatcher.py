from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import dataclasses
import logging
from typing import Any, Callable, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclasses.dataclass
class CallbackResult:
    pass


@dataclasses.dataclass
class EmptyCallbackResult(CallbackResult):
    pass


CallbackResultT = TypeVar("CallbackResultT", bound=CallbackResult)


@dataclasses.dataclass(frozen=True)
class CallbackApi(Generic[CallbackResultT]):
    pass


@dataclasses.dataclass
class CallbackState:
    failure: Exception | None
    callback_result: CallbackResult


class CallbackDispatcher:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self.states: dict[CallbackApi[Any], CallbackState] = {}
        self.futures: dict[CallbackApi[Any], asyncio.Future[Any]] = {}

    async def perform_and_wait(
        self,
        dispatch_func: Callable[[], T],
        callback_api: CallbackApi[CallbackResultT],
    ) -> tuple[T, CallbackResultT]:
        """
        Perform an API call and wait for the callback result.

        :param dispatch_func:
                The API function to call, that triggers the callback.
                Must raise :class:`BleakError` on failure.
        :param callback_api:
                The callback to wait for to get the result.
        :return:
                Tuple of (dispatch result, callback result).
        """
        dispatch_result, state = self.dispatch(dispatch_func, callback_api)

        try:
            callback_result = await state
        finally:
            self.futures.pop(callback_api, None)

        logger.debug(f"{callback_api} succeeded {callback_result}")

        return dispatch_result, callback_result

    def dispatch(
        self,
        dispatch_func: Callable[[], T],
        callback_api: CallbackApi[CallbackResultT],
    ) -> tuple[T, asyncio.Future[CallbackResultT]]:
        """Register the callback future and invoke dispatch_func synchronously.

        Returns the future to await for the callback result (and optionally the
        dispatch result as the first element of a tuple if return_dispatch_result=True).
        Prefer :meth:`perform_and_wait` for the common case. Use this method
        directly when you need the future even if the await fails
        (e.g. for cleanup on timeout).

        The dispatch_func must raise :class:`BleakError` on failure.
        """
        logger.debug(f"Waiting for android api {callback_api}")

        # Create a future, that is filled from the callback
        state: asyncio.Future[CallbackResultT] = self._loop.create_future()
        self.futures[callback_api] = state

        # Call the dispatch function, which will trigger the callback to fill the future
        try:
            dispatch_result = dispatch_func()
        except BaseException:
            del self.futures[callback_api]
            raise

        return dispatch_result, state

    def result_state_threadsafe(
        self,
        failure: Exception | None,
        callback_api: CallbackApi[CallbackResultT],
        callback_result: CallbackResultT,
    ):
        self._loop.call_soon_threadsafe(
            self._result_state, failure, callback_api, callback_result
        )

    def _result_state(
        self,
        exception: Exception | None,
        callback_api: CallbackApi[CallbackResultT],
        callback_result: CallbackResultT,
    ):
        logger.debug(
            f"Java state transfer {callback_api} error={exception} callback_result={callback_result}"
        )
        self.states[callback_api] = CallbackState(exception, callback_result)
        future = self.futures.get(callback_api, None)
        if future is not None and not future.done():
            if exception is None:
                future.set_result(callback_result)
            else:
                future.set_exception(exception)
        else:
            if exception is not None:
                # An error arrived for a callback that nobody is waiting for.
                # This can theoretically happen, but currently there is no way
                # to reproduce this. If it does happen, we log it as a warning
                # but otherwise ignore it, since there is no way to propagate the
                # error to any caller.
                logger.warning(
                    f"Ignoring error for {callback_api} with no waiting future: {exception}"
                )
