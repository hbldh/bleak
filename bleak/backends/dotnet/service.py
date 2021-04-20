from typing import List

from bleak.backends.service import BleakGATTService
from bleak.backends.dotnet.characteristic import BleakGATTCharacteristicDotNet

# Import of BleakBridge to enable loading of winrt bindings
from BleakBridge import Bridge  # noqa: F401

from Windows.Devices.Bluetooth.GenericAttributeProfile import GattDeviceService


class BleakGATTServiceDotNet(BleakGATTService):
    """GATT Characteristic implementation for the .NET backend"""

    def __init__(self, obj: GattDeviceService):
        super().__init__(obj)
        self.__characteristics = []

    @property
    def handle(self) -> int:
        """The handle of this service"""
        return int(self.obj.AttributeHandle)

    @property
    def uuid(self) -> str:
        """UUID for this service."""
        return self.obj.Uuid.ToString()

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicDotNet]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicDotNet):
        """Add a :py:class:`~BleakGATTCharacteristicDotNet` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
