from typing import Union, List

from bleak.backends.service import BleakGATTService
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.bluezdbus.characteristic import BleakGATTCharacteristicBlueZDBus


class BleakGATTServiceBlueZDBus(BleakGATTService):
    def __init__(self, obj, path):
        super().__init__(obj)
        self.__characteristics = []
        self.__path = path

    @property
    def uuid(self) -> str:
        return self.obj["UUID"]

    @property
    def description(self) -> str:
        return super(BleakGATTServiceBlueZDBus, self).description

    @property
    def characteristics(self) -> List:
        return self.__characteristics

    def get_characteristic(self, _uuid) -> Union[BleakGATTCharacteristic, None]:
        raise NotImplementedError()

    def add_characteristic(self, characteristic: BleakGATTCharacteristicBlueZDBus):
        self.__characteristics.append(characteristic)

    @property
    def path(self):
        return self.__path
