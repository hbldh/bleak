import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

from collections.abc import Iterable
from typing import Any

from bleak._compat import Self, override
from bleak.args.bluez import BlueZAdapterArgs
from bleak.backends.adapter import BaseBleakAdapter
from bleak.backends.bluezdbus.manager import get_global_bluez_manager
from bleak.backends.bluezdbus.utils import device_name_from_props
from bleak.backends.device import BLEDevice


class BleakAdapterBlueZDBus(BaseBleakAdapter):
    """The native Linux Bleak BLE Adapter."""

    def __init__(self, adapter_path: str):
        self._adapter_path = adapter_path

    @classmethod
    @override
    async def get(cls, *, bluez: BlueZAdapterArgs = {}, **kwargs: Any) -> Self:
        manager = await get_global_bluez_manager()
        adapter = bluez.get("adapter")
        adapter_path = (
            f"/org/bluez/{adapter}" if adapter else manager.get_default_adapter()
        )
        return cls(adapter_path)

    @override
    async def get_connected_devices(
        self, service_uuids: Iterable[str]
    ) -> list[BLEDevice]:
        manager = await get_global_bluez_manager()
        devices: list[BLEDevice] = []

        for path, props in manager.get_connected_devices(
            self._adapter_path, service_uuids
        ):
            address = props["Address"]
            name = device_name_from_props(props)
            devices.append(BLEDevice(address, name, {"path": path, "props": props}))

        return devices
