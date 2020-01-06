"""
Perform Bluetooth LE Scan.

macOS

Created on 2019-06-24 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
from asyncio.events import AbstractEventLoop
from typing import List

from bleak.backends.corebluetooth import CBAPP as cbapp
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

async def discover(
    timeout: float = 5.0, loop: AbstractEventLoop = None, **kwargs
) -> List[BLEDevice]:
    """Perform a Bluetooth LE Scan.

    Args:
        timeout (float): duration of scanning period
        loop (Event Loop): Event Loop to use

    """
    loop = loop if loop else asyncio.get_event_loop()

    if not cbapp.central_manager_delegate.enabled:
        raise BleakError("Bluetooth device is turned off")

    scan_options = {"timeout": timeout}

    await cbapp.central_manager_delegate.scanForPeripherals_(scan_options)

    # CoreBluetooth doesn't explicitly use MAC addresses to identify peripheral
    # devices because private devices may obscure their MAC addresses. To cope
    # with this, CoreBluetooth utilizes UUIDs for each peripheral. We'll use
    # this for the BLEDevice address on macOS


    devices = cbapp.central_manager_delegate.devices
    return list(devices.values())

