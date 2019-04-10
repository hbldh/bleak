from typing import List, Union

from bleak.backends.service import BleakGATTService
from bleak.backends.dotnet.characteristic import BleakGATTCharacteristicDotNet

from Windows.Devices.Bluetooth.GenericAttributeProfile import GattDeviceService


class BleakGATTServiceDotNet(BleakGATTService):
    """GATT Characteristic implementation for the .NET backend"""

    def __init__(self, obj: GattDeviceService):
        super().__init__(obj)
        self.__characteristics = [
            # BleakGATTCharacteristicDotNet(c) for c in obj.GetAllCharacteristics()
        ]

    @property
    def uuid(self):
        return self.obj.Uuid.ToString()

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicDotNet]:
        """List of characteristics for this service"""
        return self.__characteristics

    def get_characteristic(self, _uuid) -> Union[BleakGATTCharacteristicDotNet, None]:
        """Get a characteristic by UUID"""
        try:
            return next(filter(lambda x: x.uuid == _uuid, self.characteristics))
        except StopIteration:
            return None

    def add_characteristic(self, characteristic: BleakGATTCharacteristicDotNet):
        """Add a :py:class:`~BleakGATTCharacteristicDotNet` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
