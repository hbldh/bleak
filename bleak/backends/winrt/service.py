import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "win32":
        assert False, "This backend is only available on Windows"

from winrt.windows.devices.bluetooth.genericattributeprofile import GattDeviceService

from bleak.backends.service import BleakGATTService
from bleak.backends.winrt.characteristic import BleakGATTCharacteristicWinRT


class BleakGATTServiceWinRT(BleakGATTService):
    """GATT Characteristic implementation for the .NET backend, implemented with WinRT"""

    def __init__(self, obj: GattDeviceService) -> None:
        super().__init__(obj)
        self.__characteristics: list[BleakGATTCharacteristicWinRT] = []

    @property
    def uuid(self) -> str:
        return str(self.obj.uuid)

    @property
    def handle(self) -> int:
        return self.obj.attribute_handle

    @property
    def characteristics(self) -> list[BleakGATTCharacteristicWinRT]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicWinRT) -> None:
        """Add a :py:class:`~BleakGATTCharacteristicWinRT` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
