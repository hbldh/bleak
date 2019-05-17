from typing import Union, List

from bleak.backends.service import BleakGATTService
from bleak.backends.bluezdbus.characteristic import BleakGATTCharacteristicBlueZDBus


class BleakGATTServiceBlueZDBus(BleakGATTService):
    """GATT Service implementation for the BlueZ DBus backend"""

    def __init__(self, obj, path):
        super().__init__(obj)
        self.__characteristics = []
        self.__path = path

    @property
    def uuid(self) -> str:
        """The UUID to this service"""
        return self.obj["UUID"]

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicBlueZDBus]:
        """List of characteristics for this service"""
        return self.__characteristics

    def get_characteristic(
        self, _uuid
    ) -> Union[BleakGATTCharacteristicBlueZDBus, None]:
        """Get a characteristic by UUID"""
        raise NotImplementedError()

    def add_characteristic(self, characteristic: BleakGATTCharacteristicBlueZDBus):
        """Add a :py:class:`~BleakGATTCharacteristicBlueZDBus` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)

    @property
    def path(self):
        """The DBus path. Mostly needed by `bleak`, not by end user"""
        return self.__path
