import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    if sys.platform != "win32":
        assert False, "This backend is only available on Windows"

from collections.abc import Iterable

from winrt.windows.devices.bluetooth import BluetoothConnectionStatus, BluetoothLEDevice
from winrt.windows.devices.enumeration import DeviceInformation

from bleak._compat import Self, override
from bleak.backends.adapter import BaseBleakAdapter
from bleak.backends.device import BLEDevice
from bleak.backends.winrt.util import assert_mta, format_bdaddr


class BleakAdapterWinRT(BaseBleakAdapter):
    """The native Windows Bleak BLE Adapter."""

    @classmethod
    @override
    async def get(cls, **kwargs: Any) -> Self:
        await assert_mta()
        return cls()

    @override
    async def get_connected_devices(
        self, service_uuids: Iterable[str]
    ) -> list[BLEDevice]:
        # service_uuids is ignored on Windows: the BluetoothLEDevice
        # selector already excludes Bluetooth Classic devices.
        selector = BluetoothLEDevice.get_device_selector_from_connection_status(
            BluetoothConnectionStatus.CONNECTED
        )
        device_info_collection = await DeviceInformation.find_all_async_aqs_filter(
            selector
        )

        devices: list[BLEDevice] = []

        for i in range(device_info_collection.size):
            device_info = device_info_collection.get_at(i)
            ble_device = await BluetoothLEDevice.from_id_async(device_info.id)
            address = format_bdaddr(ble_device.bluetooth_address)
            devices.append(BLEDevice(address, device_info.name, device_info))
            ble_device.close()

        return devices
