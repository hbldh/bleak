import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "win32":
        assert False, "This backend is only available on Windows"

from winrt.windows.devices.bluetooth.genericattributeprofile import GattDeviceService

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTService


class BleakGATTServiceWinRT(BleakGATTService):
    """GATT Characteristic implementation for the .NET backend, implemented with WinRT"""

    def __init__(self, obj: GattDeviceService) -> None:
        super().__init__(obj)
        self.__characteristics: list[BleakGATTCharacteristic] = []

    @property
    def uuid(self) -> str:
        return str(self.obj.uuid)

    @property
    def handle(self) -> int:
        return self.obj.attribute_handle

    @property
    def characteristics(self) -> list[BleakGATTCharacteristic]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristic) -> None:
        """Add a :py:class:`~BleakGATTCharacteristic` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
