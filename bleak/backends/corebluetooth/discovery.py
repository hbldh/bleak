
"""
Perform Bluetooth LE Scan.

macOS

Created on 2019-06-24 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio

from typing import List
from asyncio.events import AbstractEventLoop
from bleak.backends.device import BLEDevice
from ..corebluetooth import CBAPP as cbapp
from bleak.exc import BleakError

async def discover(
        timeout: float = 5.0,
        loop: AbstractEventLoop = None,
        **kwargs) -> List[BLEDevice]:
    """Perform a Bluetooth LE Scan.

    Args:
        timeout (float): duration of scaning period
        loop (Event Loop): Event Loop to use

    """
    loop = loop if loop else asyncio.get_event_loop()

    devices = {}

    # Need to call search for Peripherals
    # This should be a function of the CBCentralManager
    # CentralManager will be maintained by the
    # CBCentralManagerDelegate
    # We should only have one instance of CBCentralManagerDelegate
    # Possibly initialize it on the init and init it if it is not

    if not cbapp.central_manager_delegate.enabled:
        raise BleakError("Bluetooth device is turned off")

    scan_options = {
            'timeout': 5
            }

    await cbapp.central_manager_delegate.scanForPeripherals_(scan_options)

    return []
