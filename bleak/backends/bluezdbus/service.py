from typing import List

from bleak.backends.bluezdbus.utils import extract_service_handle_from_path
from bleak.backends.service import BleakGATTService
from bleak.backends.bluezdbus.characteristic import BleakGATTCharacteristicBlueZDBus


class BleakGATTServiceBlueZDBus(BleakGATTService):
    """GATT Service implementation for the BlueZ DBus backend"""

    def __init__(self, obj, path):
        """Should not be called by end user, only by bleak itself"""
        super().__init__(obj)
        self.__characteristics = []
        self.__path = path
        self.__handle = extract_service_handle_from_path(path)

    @property
    def uuid(self) -> str:
        return self.obj["UUID"]

    @property
    def handle(self) -> int:
        return self.__handle

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicBlueZDBus]:
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicBlueZDBus):
        self.__characteristics.append(characteristic)

    @property
    def path(self):
        """The DBus path. Mostly needed by `bleak`, not by end user"""
        return self.__path
