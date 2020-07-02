"""
Perform Bluetooth LE Scan.

macOS

Created on 2019-06-24 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
from asyncio.events import AbstractEventLoop
from typing import List

from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
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

    manager = CentralManagerDelegate.alloc().init()
    try:
        await manager.wait_for_powered_on(0.1)
    except asyncio.TimeoutError:
        raise BleakError("Bluetooth device is turned off")

    scan_options = {"timeout": timeout}

    await manager.scanForPeripherals_(scan_options)

    # CoreBluetooth doesn't explicitly use MAC addresses to identify peripheral
    # devices because private devices may obscure their MAC addresses. To cope
    # with this, CoreBluetooth utilizes UUIDs for each peripheral. We'll use
    # this for the BLEDevice address on macOS

    devices = manager.devices
    return list(devices.values())
