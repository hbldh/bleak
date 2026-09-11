import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    if sys.platform != "win32":
        assert False, "This backend is only available on Windows"

from uuid import UUID

from winrt.system import unbox_string, unbox_uint8
from winrt.windows.devices.bluetooth import (
    BluetoothAddressType,
    BluetoothCacheMode,
    BluetoothConnectionStatus,
    BluetoothDeviceId,
    BluetoothLEDevice,
)
from winrt.windows.devices.bluetooth.genericattributeprofile import GattDeviceService
from winrt.windows.devices.enumeration import DeviceInformation

from bleak._compat import Self, override
from bleak.backends.adapter import BaseBleakAdapter
from bleak.backends.device import BLEAddressType, BLEDevice
from bleak.backends.winrt.util import assert_mta
from bleak.uuids import normalize_uuid_16


class BleakAdapterWinRT(BaseBleakAdapter):
    """The native Windows Bleak BLE Adapter."""

    @classmethod
    @override
    async def get(cls, **kwargs: Any) -> Self:
        await assert_mta()
        return cls()

    @override
    async def get_connected_devices(
        self, service_uuids: frozenset[str]
    ) -> list[BLEDevice]:
        # service_uuids is ignored on Windows: the BluetoothLEDevice
        # selector already excludes Bluetooth Classic devices.
        selector = BluetoothLEDevice.get_device_selector_from_connection_status(
            BluetoothConnectionStatus.CONNECTED
        )
        connected_devices = (
            await DeviceInformation.find_all_async_aqs_filter_and_additional_properties(
                selector,
                [
                    "System.Devices.Aep.DeviceAddress",
                    "System.Devices.Aep.Bluetooth.Le.AddressType",
                ],
            )
        )

        devices: list[BLEDevice] = []

        # Don't waste time if the default ("Generic Attribute") service is the
        # only one we're looking for since that should always match.
        check_services = service_uuids != frozenset([normalize_uuid_16(0x1801)])

        for device_info in connected_devices:
            if check_services:
                for service in service_uuids:
                    # NB: GattDeviceService.get_device_selector_from_uuid() doesn't
                    # seem to return any results, so we have to provide a device id
                    # as well. Which means we have to check each device for each
                    # service UUID.
                    selector = GattDeviceService.get_device_selector_for_bluetooth_device_id_and_uuid_with_cache_mode(
                        BluetoothDeviceId.from_id(device_info.id),
                        UUID(service),
                        # Try to avoid I/O if we can.
                        BluetoothCacheMode.CACHED,
                    )

                    services = await DeviceInformation.find_all_async_aqs_filter(
                        selector
                    )

                    if services:
                        break
                else:
                    # No matching services, skip this device.
                    continue

            address = unbox_string(
                device_info.properties["System.Devices.Aep.DeviceAddress"]
            ).upper()

            address_type: BLEAddressType
            if address_type_prop := device_info.properties.get(
                "System.Devices.Aep.Bluetooth.Le.AddressType"
            ):
                match unbox_uint8(address_type_prop):
                    case BluetoothAddressType.PUBLIC.value:
                        address_type = BLEAddressType.PUBLIC
                    case BluetoothAddressType.RANDOM.value:
                        address_type = BLEAddressType.RANDOM
                    case _:
                        address_type = BLEAddressType.UNKNOWN
            else:
                address_type = BLEAddressType.UNKNOWN

            devices.append(
                BLEDevice(address, device_info.name, device_info, address_type)
            )

        return devices
