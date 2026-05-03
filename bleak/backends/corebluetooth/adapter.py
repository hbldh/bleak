import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

from collections.abc import Iterable
from typing import Any

from CoreBluetooth import CBUUID
from Foundation import NSArray

from bleak._compat import Self, override
from bleak.backends.adapter import BaseBleakAdapter
from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.device import BLEDevice


class BleakAdapterCoreBluetooth(BaseBleakAdapter):
    """The native macOS Bleak BLE Adapter."""

    def __init__(self, manager: CentralManagerDelegate):
        self._manager = manager

    @classmethod
    @override
    async def get(cls, **kwargs: Any) -> Self:
        manager = CentralManagerDelegate()
        await manager.wait_until_ready()
        return cls(manager)

    @override
    async def get_connected_devices(
        self, service_uuids: Iterable[str]
    ) -> list[BLEDevice]:
        cb_uuids = NSArray.arrayWithArray_(
            [CBUUID.UUIDWithString_(u) for u in service_uuids]
        )

        peripherals = (
            self._manager.central_manager.retrieveConnectedPeripheralsWithServices_(
                cb_uuids
            )
        )

        devices: list[BLEDevice] = []

        for p in peripherals:
            uuid_str = p.identifier().UUIDString()
            devices.append(BLEDevice(uuid_str, p.name(), (p, self._manager)))

        return devices
