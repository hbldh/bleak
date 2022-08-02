from typing import List

from bleak.backends.service import BleakGATTService
from bleak.backends.p4android.characteristic import BleakGATTCharacteristicP4Android


class BleakGATTServiceP4Android(BleakGATTService):
    """GATT Service implementation for the python-for-android backend"""

    def __init__(self, java):
        """Should not be called by end user, only by bleak itself"""
        super().__init__(java)
        self.__uuid = self.obj.getUuid().toString()
        self.__handle = self.obj.getInstanceId()
        self.__characteristics = []

    @property
    def uuid(self) -> str:
        return self.__uuid

    @property
    def handle(self) -> int:
        return self.__handle

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicP4Android]:
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicP4Android):
        self.__characteristics.append(characteristic)
