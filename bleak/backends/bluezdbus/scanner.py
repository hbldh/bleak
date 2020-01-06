import logging
import asyncio
import pathlib
import uuid
from asyncio.events import AbstractEventLoop
from functools import wraps
from typing import Callable, Any, Union, List

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import BaseBleakScanner


logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


class BleakScannerBlueZDBus(BaseBleakScanner):
    """The native Linux Bleak BLE Scanner.

    Args:
        loop (asyncio.events.AbstractEventLoop): The event loop to use.

    Keyword Args:

    """
    def __init__(self, loop: AbstractEventLoop = None, **kwargs):
        super(BleakScannerBlueZDBus, self).__init__(loop, **kwargs)

    async def start(self):
        raise NotImplementedError()

    async def stop(self):
        raise NotImplementedError()

    async def set_scanning_filter(self, **kwargs):
        raise NotImplementedError()

    async def get_discovered_devices(self) -> List[BLEDevice]:
        raise NotImplementedError()

    def register_detection_callback(self, callback: Callable):
        raise NotImplementedError()
