import logging
from typing import Any, Dict, List, Optional

import objc
from Foundation import NSArray, NSUUID, NSBundle
from CoreBluetooth import CBPeripheral
from typing_extensions import Literal

from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import (
    AdvertisementDataCallback,
    BaseBleakScanner,
    AdvertisementData,
)
from bleak.exc import BleakError

logger = logging.getLogger(__name__)


class BleakScannerCoreBluetooth(BaseBleakScanner):
    """The native macOS Bleak BLE Scanner.

    Documentation:
    https://developer.apple.com/documentation/corebluetooth/cbcentralmanager

    CoreBluetooth doesn't explicitly use Bluetooth addresses to identify peripheral
    devices because private devices may obscure their Bluetooth addresses. To cope
    with this, CoreBluetooth utilizes UUIDs for each peripheral. Bleak uses
    this for the BLEDevice address on macOS.

    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received. Required on
            macOS >= 12.0, < 12.3 (unless you create an app with ``py2app``).
        scanning_mode:
            Set to ``"passive"`` to avoid the ``"active"`` scanning mode. Not
            supported on macOS! Will raise :class:`BleakError` if set to
            ``"passive"``
        **timeout (float):
             The scanning timeout to be used, in case of missing
            ``stopScan_`` method.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[List[str]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        **kwargs
    ):
        super(BleakScannerCoreBluetooth, self).__init__(
            detection_callback, service_uuids
        )

        if scanning_mode == "passive":
            raise BleakError("macOS does not support passive scanning")

        self._identifiers: Optional[Dict[NSUUID, Dict[str, Any]]] = None
        self._manager = CentralManagerDelegate.alloc().init()
        self._timeout: float = kwargs.get("timeout", 5.0)
        if (
            objc.macos_available(12, 0)
            and not objc.macos_available(12, 3)
            and not self._service_uuids
        ):
            # See https://github.com/hbldh/bleak/issues/720
            if NSBundle.mainBundle().bundleIdentifier() == "org.python.python":
                logger.error(
                    "macOS 12.0, 12.1 and 12.2 require non-empty service_uuids kwarg, otherwise no advertisement data will be received"
                )

    async def start(self):
        self._identifiers = {}

        def callback(p: CBPeripheral, a: Dict[str, Any], r: int) -> None:
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

            service_uuids = [
                cb_uuid_to_str(u) for u in a.get("kCBAdvDataServiceUUIDs", [])
            ]

            advertisement_data = AdvertisementData(
                local_name=p.name(),
                manufacturer_data=manufacturer_data,
                service_data=service_data,
                service_uuids=service_uuids,
                platform_data=(p, a, r),
            )

            device = BLEDevice(
                p.identifier().UUIDString(),
                p.name(),
                p,
                r,
                uuids=service_uuids,
                manufacturer_data=manufacturer_data,
                service_data=service_data,
                delegate=self._manager.central_manager.delegate(),
            )

            self._callback(device, advertisement_data)

        self._manager.callbacks[id(self)] = callback
        await self._manager.start_scan(self._service_uuids)

    async def stop(self):
        await self._manager.stop_scan()
        self._manager.callbacks.pop(id(self), None)

    def set_scanning_filter(self, **kwargs):
        """Set scanning filter for the scanner.

        .. note::

            This is not implemented for macOS yet.

        Raises:

           ``NotImplementedError``

        """
        raise NotImplementedError(
            "Need to evaluate which macOS versions to support first..."
        )

    @property
    def discovered_devices(self) -> List[BLEDevice]:
        found = []
        peripherals = self._manager.central_manager.retrievePeripheralsWithIdentifiers_(
            NSArray(self._identifiers.keys()),
        )

        for peripheral in peripherals:
            address = peripheral.identifier().UUIDString()
            name = peripheral.name() or "Unknown"
            details = peripheral
            rssi = self._manager.devices[address].rssi

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

            service_data = {}
            adv_service_data = advertisementData.get("kCBAdvDataServiceData", [])
            for u in adv_service_data:
                service_data[cb_uuid_to_str(u)] = bytes(adv_service_data[u])

            found.append(
                BLEDevice(
                    address,
                    name,
                    details,
                    rssi=rssi,
                    uuids=uuids,
                    manufacturer_data=manufacturer_data,
                    service_data=service_data,
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
