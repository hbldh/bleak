import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

from typing import Any

from bleak._compat import Self, override
from bleak.args.bluez import BlueZAdapterArgs
from bleak.backends.adapter import BaseBleakAdapter
from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.manager import get_global_bluez_manager
from bleak.backends.device import BLEDevice
from bleak.exc import BleakBluetoothNotAvailableError, BleakBluetoothNotAvailableReason


class BleakAdapterBlueZDBus(BaseBleakAdapter):
    """The native Linux Bleak BLE Adapter."""

    def __init__(self, adapter_path: str):
        self._adapter_path = adapter_path

    @classmethod
    @override
    async def get(cls, *, bluez: BlueZAdapterArgs = {}, **kwargs: Any) -> Self:
        manager = await get_global_bluez_manager()
        adapter = bluez.get("adapter")

        if adapter is None:
            # get_default_adapter() already raises BleakBluetoothNotAvailableError
            # if there is no powered BLE-central adapter.
            return cls(manager.get_default_adapter())

        adapter_path = f"/org/bluez/{adapter}"
        adapter_props = manager._properties.get(  # pyright: ignore[reportPrivateUsage]
            adapter_path, {}
        ).get(defs.ADAPTER_INTERFACE)
        if adapter_props is None:
            raise BleakBluetoothNotAvailableError(
                f"Bluetooth adapter '{adapter_path}' is unavailable",
                BleakBluetoothNotAvailableReason.NO_BLUETOOTH,
            )
        if not adapter_props.get("Powered"):
            raise BleakBluetoothNotAvailableError(
                "Bluetooth adapter is not powered on",
                BleakBluetoothNotAvailableReason.POWERED_OFF,
            )

        return cls(adapter_path)

    @override
    async def get_connected_devices(
        self, service_uuids: frozenset[str]
    ) -> list[BLEDevice]:
        manager = await get_global_bluez_manager()
        devices: list[BLEDevice] = []

        for path, props in manager.get_connected_devices(
            self._adapter_path, service_uuids
        ):
            address = props["Address"]
            # BlueZ generates a name based on the address if no name is available.
            # To match other backends, we replace this with None.
            name = (
                None
                if props["Alias"] == props["Address"].replace(":", "-")
                else props["Alias"]
            )
            devices.append(BLEDevice(address, name, {"path": path, "props": props}))

        return devices
