import logging
import asyncio
import pathlib
import uuid
from asyncio.events import AbstractEventLoop
from typing import Callable, Any, Union, List

from bleak.backends.corebluetooth import CBAPP as cbapp
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak.backends.scanner import BaseBleakScanner
from functools import partial


logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


class BleakScannerCoreBluetooth(BaseBleakScanner):
    """The native macOS Bleak BLE Scanner.

    Documentation:
    https://developer.apple.com/documentation/corebluetooth/cbcentralmanager

    CoreBluetooth doesn't explicitly use MAC addresses to identify peripheral
    devices because private devices may obscure their MAC addresses. To cope
    with this, CoreBluetooth utilizes UUIDs for each peripheral. Bleak uses
    this for the BLEDevice address on macOS.

    Args:
        loop (asyncio.events.AbstractEventLoop): The event loop to use.

    """
    def __init__(self, loop: AbstractEventLoop = None, **kwargs):
        super(BleakScannerCoreBluetooth, self).__init__(loop, **kwargs)

        if not cbapp.central_manager_delegate.enabled:
            raise BleakError("Bluetooth device is turned off")

        self._filters = kwargs.get("filters", {})

        self._callback = None
        self._found = []


    def discovered(self, device):
        logger.info("scanner discovered: {0}".format(device))
        # TODO: Check filters as needed
        self._found.append(device)
        if self._callback != None:
            self._callback(device)

    async def start(self):
        # TODO: Figure out filtering part
        self._found = []
        cbapp.central_manager_delegate.setdiscovercallback_(self.discovered)        
        cbapp.central_manager_delegate.scanForPeripherals_({"timeout":None, "filters":self._filters})

    async def stop(self):
        cbapp.central_manager_delegate.central_manager.stopScan()
        cbapp.central_manager_delegate.setdiscovercallback_(None)

    async def set_scanning_filter(self, **kwargs):
        self._filters = kwargs.get("filters", {})
        raise NotImplementedError("Need to evaluate which macOS versions to support first...")

    async def get_discovered_devices(self) -> List[BLEDevice]:
        # TODO: Figure out consistent returned devices
        # found = []
        # peripherals = cbapp.central_manager_delegate.devices

        # for i, peripheral in enumerate(peripherals):
        #     address = peripheral.identifier().UUIDString()
        #     name = peripheral.name() or "Unknown"
        #     details = peripheral

        #     advertisementData = cbapp.central_manager_delegate.advertisement_data_list[i]
        #     manufacturer_binary_data = advertisementData.get("kCBAdvDataManufacturerData")
        #     manufacturer_data = {}
        #     if manufacturer_binary_data:
        #         manufacturer_id = int.from_bytes(
        #             manufacturer_binary_data[0:2], byteorder="little"
        #         )
        #         manufacturer_value = bytes(manufacturer_binary_data[2:])
        #         manufacturer_data = {manufacturer_id: manufacturer_value}

        #     uuids = [
        #         # converting to lower case to match other platforms
        #         str(u).lower()
        #         for u in advertisementData.get("kCBAdvDataServiceUUIDs", [])
        #     ]

        #     found.append(
        #         BLEDevice(
        #             address, name, details, uuids=uuids, manufacturer_data=manufacturer_data
        #         )
        #     )

        return self._found

    def register_detection_callback(self, callback: Callable):
        self._callback = callback

    # macOS specific methods

    @property
    async def is_scanning(self):
        # TODO: Fix this???
        return cbapp.central_manager_delegate.central_manager.isScanning()


