import logging
import pathlib
from typing import Any, Dict, List

from Foundation import NSArray
from CoreBluetooth import CBPeripheral

from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import BaseBleakScanner, AdvertisementData

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


class BleakScannerCoreBluetooth(BaseBleakScanner):
    """The native macOS Bleak BLE Scanner.

    Documentation:
    https://developer.apple.com/documentation/corebluetooth/cbcentralmanager

    CoreBluetooth doesn't explicitly use Bluetooth addresses to identify peripheral
    devices because private devices may obscure their Bluetooth addresses. To cope
    with this, CoreBluetooth utilizes UUIDs for each peripheral. Bleak uses
    this for the BLEDevice address on macOS.

    Keyword Args:
        timeout (double): The scanning timeout to be used, in case of missing
          ``stopScan_`` method.

    """

    def __init__(self, **kwargs):
        super(BleakScannerCoreBluetooth, self).__init__(**kwargs)
        self._identifiers = None
        self._manager = CentralManagerDelegate.alloc().init()
        self._timeout = kwargs.get("timeout", 5.0)

    async def start(self):
        self._identifiers = {}

        def callback(p: CBPeripheral, a: Dict[str, Any], r: int):
            # update identifiers for scanned device
            self._identifiers.setdefault(p.identifier(), {}).update(a)

            if not self._callback:
                return

            # Process service data
            service_data_dict_raw = a.get("kCBAdvDataServiceData", {})
            service_data = {
                cb_uuid_to_str(k): bytes(v) for k, v in service_data_dict_raw.items()
            }

            # Process manufacturer data into a more friendly format
            manufacturer_binary_data = a.get("kCBAdvDataManufacturerData")
            manufacturer_data = {}
            if manufacturer_binary_data:
                manufacturer_id = int.from_bytes(
                    manufacturer_binary_data[0:2], byteorder="little"
                )
                manufacturer_value = bytes(manufacturer_binary_data[2:])
                manufacturer_data[manufacturer_id] = manufacturer_value

            advertisement_data = AdvertisementData(
                local_name=p.name(),
                manufacturer_data=manufacturer_data,
                service_data=service_data,
                service_uuids=[
                    cb_uuid_to_str(u) for u in a.get("kCBAdvDataServiceUUIDs", [])
                ],
                platform_data=(p, a, r),
            )

            device = BLEDevice(p.identifier().UUIDString(), p.name(), p, r)

            self._callback(device, advertisement_data)

        self._manager.callbacks[id(self)] = callback
        self._manager.start_scan({})

    async def stop(self):
        del self._manager.callbacks[id(self)]
        try:
            await self._manager.stop_scan()
        except Exception as e:
            logger.warning("stopScan method could not be called: {0}".format(e))

    async def set_scanning_filter(self, **kwargs):
        """Set scanning filter for the scanner.

        .. note::

            This is not implemented for macOS yet.

        Raises:

           ``NotImplementedError``

        """
        raise NotImplementedError(
            "Need to evaluate which macOS versions to support first..."
        )

    async def get_discovered_devices(self) -> List[BLEDevice]:
        found = []
        peripherals = self._manager.central_manager.retrievePeripheralsWithIdentifiers_(
            NSArray(self._identifiers.keys()),
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
                cb_uuid_to_str(u)
                for u in advertisementData.get("kCBAdvDataServiceUUIDs", [])
            ]

            found.append(
                BLEDevice(
                    address,
                    name,
                    details,
                    uuids=uuids,
                    manufacturer_data=manufacturer_data,
                    delegate=self._manager.central_manager.delegate(),
                )
            )

        return found

    # macOS specific methods

    @property
    def is_scanning(self):
        # TODO: Evaluate if newer macOS than 10.11 has isScanning.
        try:
            return self._manager.isScanning_
        except Exception:
            return None
