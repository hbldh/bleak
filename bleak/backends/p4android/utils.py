# -*- coding: utf-8 -*-

import asyncio
import logging
import warnings
from typing import List, Optional

from android.permissions import Permission
from android.permissions import request_permissions as request_android_permissions
from jnius import PythonJavaClass

from ...exc import BleakError
from . import defs

logger = logging.getLogger(__name__)


class AsyncJavaCallbacks(PythonJavaClass):
    __javacontext__ = "app"

    def __init__(self, loop: asyncio.AbstractEventLoop):
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
                f"Not waiting for android api {resultApi} because found {resultExpected}"
            )
        else:
            logger.debug(f"Waiting for android api {resultApi}")

            state = self._loop.create_future()
            self.futures[resultApi] = state
            result1 = dispatchApi(*dispatchParams)
            if return_indicates_status and not result1:
                del self.futures[resultApi]
                raise BleakError(f"api call failed, not waiting for {resultApi}")
            data = await state
            result2 = self._if_expected(data, resultExpected)
            if result2 is None:
                raise BleakError("Expected", resultExpected, "got", data)

            logger.debug(f"{resultApi} succeeded {result2}")

        if return_indicates_status:
            return result2
        else:
            return (result1, *result2)

    def _result_state_unthreadsafe(self, failure_str, source, data):
        logger.debug(f"Java state transfer {source} error={failure_str} data={data}")
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
                        warnings.warn(f"Redirecting error without home to {name}")
                        future.set_exception(exception)
                else:
                    # send it on the event thread
                    raise exception

async def request_permissions(permissions: Optional[List[str]] = None) -> None:
    loop = asyncio.get_running_loop()
    permission_acknowledged = loop.create_future()
    def handle_permissions(permissions, grantResults):
        if any(grantResults):
            loop.call_soon_threadsafe(
                permission_acknowledged.set_result, grantResults
            )
        else:
            loop.call_soon_threadsafe(
                permission_acknowledged.set_exception(
                    BleakError("User denied access to " + str(permissions))
                )
            )
    if permissions is None:
        permissions = [
            Permission.ACCESS_FINE_LOCATION,
            Permission.ACCESS_COARSE_LOCATION,
            Permission.ACCESS_BACKGROUND_LOCATION,
        ]
        if defs.VERSION.SDK_INT >= 31:
            permissions.extend([
                Permission.BLUETOOTH_SCAN,
                Permission.BLUETOOTH_CONNECT,
            ])
    request_android_permissions(
            permissions,
            handle_permissions,
        )
    await permission_acknowledged
