# -*- coding: utf-8 -*-

import logging
import warnings

from jnius import PythonJavaClass

from bleak.exc import BleakError

logger = logging.getLogger(__name__)


class AsyncJavaCallbacks(PythonJavaClass):
    __javacontext__ = "app"

    def __init__(self, loop):
        self._loop = loop
        self.states = {}
        self.futures = {}

    @staticmethod
    def _if_expected(result, expected):
        if result[: len(expected)] == expected[:]:
            return result[len(expected) :]
        else:
            return None

    async def perform_and_wait(
        self,
        dispatchApi,
        dispatchParams,
        resultApi,
        resultExpected=(),
        unless_already=False,
        return_indicates_status=True,
    ):
        result2 = None
        if unless_already:
            if resultApi in self.states:
                result2 = self._if_expected(self.states[resultApi][1:], resultExpected)
                result1 = True

        if result2 is not None:
            logger.debug(
                "Not waiting for android api {0} because found {1}".format(
                    resultApi, resultExpected
                )
            )
        else:
            logger.debug("Waiting for android api {0}".format(resultApi))

            state = self._loop.create_future()
            self.futures[resultApi] = state
            result1 = dispatchApi(*dispatchParams)
            if return_indicates_status and not result1:
                del self.futures[resultApi]
                raise BleakError(
                    "api call failed, not waiting for {}".format(resultApi)
                )
            data = await state
            result2 = self._if_expected(data, resultExpected)
            if result2 is None:
                raise BleakError("Expected", resultExpected, "got", data)

            logger.debug("{0} succeeded {1}".format(resultApi, result2))

        if return_indicates_status:
            return result2
        else:
            return (result1, *result2)

    def _result_state_unthreadsafe(self, failure_str, source, data):
        logger.debug(
            "Java state transfer {0} error={1} data={2}".format(
                source, failure_str, data
            )
        )
        self.states[source] = (failure_str, *data)
        future = self.futures.get(source, None)
        if future is not None and not future.done():
            if failure_str is None:
                future.set_result(data)
            else:
                future.set_exception(BleakError(source, failure_str, *data))
        else:
            if failure_str is not None:
                # an error happened with nothing waiting for it
                exception = BleakError(source, failure_str, *data)
                namedfutures = [
                    namedfuture
                    for namedfuture in self.futures.items()
                    if not namedfuture[1].done()
                ]
                if len(namedfutures):
                    # send it on existing requests
                    for name, future in namedfutures:
                        warnings.warn(
                            "Redirecting error without home to {0}".format(name)
                        )
                        future.set_exception(exception)
                else:
                    # send it on the event thread
                    raise exception
