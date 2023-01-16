from typing import List

from ..service import BleakGATTService
from .characteristic import BleakGATTCharacteristicBGAPI


class BleakGATTServiceBGAPI(BleakGATTService):
    """GATT Service implementation for the Silicon Labs BGAPI backend"""

    def __init__(self, obj):
        super().__init__(obj)
        # Blah, named tuples or something would have been nicer?
        self.__uuid = self.obj["uuid"]
        self.__handle = self.obj["handle"]
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
    def characteristics(self) -> List[BleakGATTCharacteristicBGAPI]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicBGAPI):
        """Add a :py:class:`~BleakGATTCharacteristicBGAPI` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
