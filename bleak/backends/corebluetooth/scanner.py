import logging
import asyncio
import pathlib
import uuid
from asyncio.events import AbstractEventLoop
from typing import Callable, Any, Union, List

from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak.backends.scanner import BaseBleakScanner


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
          ``stopScan_`` method.

    """

    def __init__(self, loop: AbstractEventLoop = None, **kwargs):
        super(BleakScannerCoreBluetooth, self).__init__(loop, **kwargs)
        self._callback = None
        self._identifiers = None
        self._manager = CentralManagerDelegate.alloc().init()
        self._timeout = kwargs.get("timeout", 5.0)

    async def start(self):
        try:
            await self._manager.wait_for_powered_on(0.1)
        except asyncio.TimeoutError:
            raise BleakError("Bluetooth device is turned off")

        self._identifiers = {}

        def callback(p, a, r):
            self._identifiers[p.identifier()] = a
            if self._callback:
                self._callback((p, a, r))

        self._manager.callbacks[id(self)] = callback

        # TODO: Evaluate if newer macOS than 10.11 has stopScan.
        if hasattr(self._manager, "stopScan_"):
            await self._manager.scanForPeripherals_()
        else:
            await self._manager.scanForPeripherals_({"timeout": self._timeout})

    async def stop(self):
        del self._manager.callbacks[id(self)]
        try:
            await self._manager.stopScan_()
        except Exception as e:
            logger.warning("stopScan method could not be called: {0}".format(e))

    async def set_scanning_filter(self, **kwargs):
        raise NotImplementedError(
            "Need to evaluate which macOS versions to support first..."
        )

    async def get_discovered_devices(self) -> List[BLEDevice]:
        found = []
        peripherals = self._manager.central_manager.retrievePeripheralsWithIdentifiers_(
            self._identifiers.keys(),
        )

        for i, peripheral in enumerate(peripherals):
            address = peripheral.identifier().UUIDString()
            name = peripheral.name() or "Unknown"
            details = peripheral

            advertisementData = self._identifiers[peripheral.identifier()]
            manufacturer_binary_data = advertisementData.get(
                "kCBAdvDataManufacturerData"
            )
            manufacturer_data = {}
            if manufacturer_binary_data:
                manufacturer_id = int.from_bytes(
                    manufacturer_binary_data[0:2], byteorder="little"
                )
                manufacturer_value = bytes(manufacturer_binary_data[2:])
                manufacturer_data = {manufacturer_id: manufacturer_value}

            uuids = [
                # converting to lower case to match other platforms
                str(u).lower()
                for u in advertisementData.get("kCBAdvDataServiceUUIDs", [])
            ]

            found.append(
                BLEDevice(
                    address,
                    name,
                    details,
                    uuids=uuids,
                    manufacturer_data=manufacturer_data,
                )
            )

        return found

    def register_detection_callback(self, callback: Callable):
        self._callback = callback

    # macOS specific methods

    @property
    def is_scanning(self):
        # TODO: Evaluate if newer macOS than 10.11 has isScanning.
        try:
            return self._manager.isScanning_
        except:
            return None
