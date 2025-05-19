import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTService


class BleakGATTServiceP4Android(BleakGATTService):
    """GATT Service implementation for the python-for-android backend"""

    def __init__(self, java):
        super().__init__(java)
        self.__uuid = self.obj.getUuid().toString()
        self.__handle = self.obj.getInstanceId()
        self.__characteristics = []

    @property
    def uuid(self) -> str:
        """The UUID to this service"""
        return self.__uuid

    @property
    def handle(self) -> int:
        """A unique identifier for this service"""
        return self.__handle

    @property
    def characteristics(self) -> list[BleakGATTCharacteristic]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        """Add a :py:class:`~BleakGATTCharacteristic` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
