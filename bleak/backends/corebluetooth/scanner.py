import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import logging
from typing import Any, Literal, Optional
from warnings import warn

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

import objc
from CoreBluetooth import CBPeripheral
from Foundation import NSBundle, NSDictionary

from bleak.args.corebluetooth import CBScannerArgs as _CBScannerArgs
from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from bleak.backends.scanner import (
    AdvertisementData,
    AdvertisementDataCallback,
    BaseBleakScanner,
)
from bleak.exc import BleakError

logger = logging.getLogger(__name__)


def __getattr__(name: str):
    if name == "CBScannerArgs":
        warn(
            "importing CBScannerArgs from bleak.backends.corebluetooth.scanner is deprecated, use bleak.args.corebluetooth instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return _CBScannerArgs
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
        detection_callback: Optional[AdvertisementDataCallback],
        service_uuids: Optional[list[str]],
        scanning_mode: Literal["active", "passive"],
        *,
        cb: _CBScannerArgs,
        **kwargs: Any,
    ):
        super(BleakScannerCoreBluetooth, self).__init__(
            detection_callback, service_uuids
        )

        self._use_bdaddr = cb.get("use_bdaddr", False)

        if scanning_mode == "passive":
            raise BleakError("macOS does not support passive scanning")

        manager = CentralManagerDelegate.alloc().init()
        assert manager
        self._manager = manager
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

    @override
    async def start(self) -> None:
        self.seen_devices = {}

        def callback(p: CBPeripheral, a: NSDictionary, r: int) -> None:

            service_uuids = [
                cb_uuid_to_str(u) for u in a.get("kCBAdvDataServiceUUIDs", [])
            ]

            if not self.is_allowed_uuid(service_uuids):
                return

            # Process service data
            service_data_dict_raw = a.get("kCBAdvDataServiceData", {})
            service_data = {
                cb_uuid_to_str(k): bytes(v) for k, v in service_data_dict_raw.items()
            }

            # Process manufacturer data into a more friendly format
            manufacturer_binary_data = a.get("kCBAdvDataManufacturerData")
            manufacturer_data: dict[int, bytes] = {}
            if manufacturer_binary_data:
                manufacturer_id = int.from_bytes(
                    manufacturer_binary_data[0:2], byteorder="little"
                )
                manufacturer_value = bytes(manufacturer_binary_data[2:])
                manufacturer_data[manufacturer_id] = manufacturer_value

            # set tx_power data if available
            tx_power = a.get("kCBAdvDataTxPowerLevel")

            advertisement_data = AdvertisementData(
                local_name=a.get("kCBAdvDataLocalName"),
                manufacturer_data=manufacturer_data,
                service_data=service_data,
                service_uuids=service_uuids,
                tx_power=tx_power,
                rssi=r,
                platform_data=(p, a, r),
            )

            if self._use_bdaddr:
                # HACK: retrieveAddressForPeripheral_ is undocumented but seems to do the trick
                address_bytes: Optional[bytes] = (
                    self._manager.central_manager.retrieveAddressForPeripheral_(p)
                )
                if address_bytes is None:
                    logger.debug(
                        "Could not get Bluetooth address for %s. Ignoring this device.",
                        p.identifier().UUIDString(),
                    )
                address = address_bytes.hex(":").upper()
            else:
                address = p.identifier().UUIDString()

            device = self.create_or_update_device(
                p.identifier().UUIDString(),
                address,
                p.name(),
                (p, self._manager.central_manager.delegate()),
                advertisement_data,
            )

            self.call_detection_callbacks(device, advertisement_data)

        self._manager.callbacks[id(self)] = callback
        await self._manager.start_scan(self._service_uuids)

    @override
    async def stop(self) -> None:
        await self._manager.stop_scan()
        self._manager.callbacks.pop(id(self), None)
