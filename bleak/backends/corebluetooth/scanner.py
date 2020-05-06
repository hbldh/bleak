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

    Keyword Args:
        timeout (double): The scanning timeout to be used, in case of missing
          ``stopScan`` metod.

    """
    def __init__(self, loop: AbstractEventLoop = None, **kwargs):
        super(BleakScannerCoreBluetooth, self).__init__(loop, **kwargs)

        if not cbapp.central_manager_delegate.enabled:
            raise BleakError("Bluetooth device is turned off")

        self._timeout = kwargs.get("timeout", 5.0)

        self._callback = None
        self._found = []

    def discovered(self, device):
        logger.warning("SCANNER discovered: {0}".format(device))
        self._found.append(device)
        print(device)
        if self._callback != None:
            self._callback(device)

    async def start(self):
        # TODO: Evaluate if newer macOS than 10.11 has stopScan.
        self._found = []
        cbapp.central_manager_delegate.setdiscovercallback_(self.discovered)
        if hasattr(cbapp.central_manager_delegate.central_manager, "stopScan"):
            service_uuids = []
        # if "service_uuids" in scan_options:
        #     service_uuids_str = scan_options["service_uuids"]
        #     service_uuids = NSArray.alloc().initWithArray_(
        #         list(map(string2uuid, service_uuids_str))
        #     )

        # timeout = 0
        # if "timeout" in scan_options:
        #     timeout = float(scan_options["timeout"])

        # self.central_manager.scanForPeripheralsWithServices_options_(
        #     service_uuids, None
        # )
            cbapp.central_manager_delegate.central_manager.scanForPeripheralsWithServices_options_(service_uuids, None)
        else:
            await cbapp.central_manager_delegate.scanForPeripherals_({"timeout": self._timeout})

    async def stop(self):
        try:
            cbapp.central_manager_delegate.central_manager.stopScan()
        except Exception as e:
            logger.warning("stopScan method could not be called: {0}".format(e))
        cbapp.central_manager_delegate.setdiscovercallback_(None)

    async def set_scanning_filter(self, **kwargs):
        raise NotImplementedError("Need to evaluate which macOS versions to support first...")

    async def get_discovered_devices(self) -> List[BLEDevice]:
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
    def is_scanning(self):
        # TODO: Evaluate if newer macOS than 10.11 has isScanning.
        try:
            return cbapp.central_manager_delegate.isScanning_
        except:
            return None


