"""
Perform Bluetooth LE Scan.

macOS

Created on 2019-06-24 by kevincar <kevincarrolldavis@gmail.com>

"""

from typing import List

from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.device import BLEDevice


async def discover(timeout: float = 5.0, **kwargs) -> List[BLEDevice]:
    """Perform a Bluetooth LE Scan.

    Args:
        timeout (float): duration of scanning period

    """
    manager = CentralManagerDelegate.alloc().init()
    scan_options = {"timeout": timeout}

    await manager.scanForPeripherals_(scan_options)

    # CoreBluetooth doesn't explicitly use Bluetooth addresses to identify peripheral
    # devices because private devices may obscure their Bluetooth addresses. To cope
    # with this, CoreBluetooth utilizes UUIDs for each peripheral. We'll use
    # this for the BLEDevice address on macOS

    devices = manager.devices
    return list(devices.values())
