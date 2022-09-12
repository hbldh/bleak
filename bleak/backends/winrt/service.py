from typing import List

from bleak_winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattDeviceService,
)

from bleak.backends.service import BleakGATTService
from bleak.backends.winrt.characteristic import BleakGATTCharacteristicWinRT


class BleakGATTServiceWinRT(BleakGATTService):
    """GATT Characteristic implementation for the .NET backend, implemented with WinRT"""

    def __init__(self, obj: GattDeviceService):
        super().__init__(obj)
        self.__characteristics = []

    @property
    def uuid(self) -> str:
        return str(self.obj.uuid)

    @property
    def handle(self) -> int:
        return self.obj.attribute_handle

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicWinRT]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicWinRT):
        """Add a :py:class:`~BleakGATTCharacteristicWinRT` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
