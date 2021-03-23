from uuid import UUID
from typing import List, Union

from bleak.backends.service import BleakGATTService
from bleak.backends.winrt.characteristic import BleakGATTCharacteristicWinRT

from winrt.windows.devices.bluetooth.genericattributeprofile import GattDeviceService


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

    def get_characteristic(
        self, _uuid: Union[str, UUID]
    ) -> Union[BleakGATTCharacteristicWinRT, None]:
        """Get a characteristic by UUID"""
        try:
            return next(filter(lambda x: x.uuid == str(_uuid), self.characteristics))
        except StopIteration:
            return None

    def add_characteristic(self, characteristic: BleakGATTCharacteristicWinRT):
        """Add a :py:class:`~BleakGATTCharacteristicWinRT` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
