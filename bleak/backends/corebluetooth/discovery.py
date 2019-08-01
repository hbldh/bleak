
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
        timeout (float): duration of scaning period
        loop (Event Loop): Event Loop to use

    """
    loop = loop if loop else asyncio.get_event_loop()

    devices = {}

    if not cbapp.central_manager_delegate.enabled:
        raise BleakError("Bluetooth device is turned off")

    scan_options = {"timeout": timeout}

    await cbapp.central_manager_delegate.scanForPeripherals_(scan_options)

    # CoreBluetooth doesn't explicitly use MAC addresses to identify peripheral
    # devices because private devices may obscure their MAC addresses. To cope
    # with this, CoreBluetooth utilizes UUIDs for each peripheral. We'll use
    # this for the BLEDevice address on macOS

    found = []

    peripherals = cbapp.central_manager_delegate.peripheral_list

    for i, peripheral in enumerate(peripherals):
        address = peripheral.identifier().UUIDString()
        name = peripheral.name() or "Unknown"
        details = peripheral

        advertisementData = cbapp.central_manager_delegate.advertisement_data_list[i]
        manufacturer_binary_data = (
            advertisementData["kCBAdvDataManufacturerData"]
            if "kCBAdvDataManufacturerData" in advertisementData.keys()
            else None
        )
        manufacturer_data = {}
        if manufacturer_binary_data:
            manufacturer_id = int.from_bytes(
                manufacturer_binary_data[0:2], byteorder="little"
            )
            manufacturer_value = "".join(
                list(
                    map(
                        lambda x: format(x, "x")
                        if len(format(x, "x")) == 2
                        else "0{}".format(format(x, "x")),
                        list(manufacturer_binary_data)[2:],
                    )
                )
            )
            manufacturer_data = {manufacturer_id: manufacturer_value}

        found.append(
            BLEDevice(address, name, details, manufacturer_data=manufacturer_data)
        )

    return found
