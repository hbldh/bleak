from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import dataclasses
import logging
from typing import TYPE_CHECKING

from android.bluetooth.le import ScanCallback, ScanResult
from java import Override, jint, jvoid, static_proxy

from bleak.backends.android.dispatcher import (
    CallbackApi,
    CallbackDispatcher,
    CallbackResult,
)
from bleak.backends.android.status import ScanFailed
from bleak.exc import BleakError

if TYPE_CHECKING:
    # Only for type checking. At runtime this results in an error.
    from bleak.backends.android.scanner import BleakScannerAndroid

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class OnScanResult(CallbackResult):
    result: "None | ScanResult"


@dataclasses.dataclass(frozen=True)
class OnScanCallback(CallbackApi[OnScanResult]):
    pass


class PythonScanCallback(static_proxy(ScanCallback)):  # type: ignore[misc]
    """Callback class for LE Scan. PRIVATE.

    This class holds methods that receive and handle
    data from Android's BluetoothLeScanner methods.
    It is not intended to call this class directly.
    """

    def __init__(self, scanner: "BleakScannerAndroid", loop: asyncio.AbstractEventLoop):
        super(PythonScanCallback, self).__init__()
        self._loop = loop
        self._scanner = scanner
        self.java = self
        self.dispatcher = CallbackDispatcher(loop)

    @Override(jvoid, [jint])
    def onScanFailed(self, errorCode: int):
        logger.debug(f"onScanFailed {errorCode=}")
        error_str = ScanFailed(int(errorCode)).name
        self.dispatcher.result_state_threadsafe(
            BleakError(f"Scan failed with error code: {int(errorCode)} ({error_str})"),
            OnScanCallback(),
            OnScanResult(None),
        )

    @Override(jvoid, [jint, ScanResult])
    def onScanResult(self, callbackType: int, result: ScanResult):
        logger.debug(f"onScanResult {callbackType=}")
        self._loop.call_soon_threadsafe(self._scanner.handle_scan_result, result)

        if OnScanCallback() not in self.dispatcher.states:
            self.dispatcher.result_state_threadsafe(
                None,
                OnScanCallback(),
                OnScanResult(result),
            )
