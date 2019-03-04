# -*- coding: utf-8 -*-
"""
__init__.py

Created on 2017-11-19 by hbldh <henrik.blidh@nedomkull.com>

"""

# Use PyObjC and PyObjC Core Bluetooth bindings for Bleak!


class BleakClientCoreBluetooth(object):
    def __init__(self, address, hci_device="hci0"):
        raise NotImplementedError("BleakClientCoreBluetooth not implemented yet.")


async def discover(device="hci0", timeout=5.0):
    raise NotImplementedError("CoreBluetooth discover not implemented yet.")
