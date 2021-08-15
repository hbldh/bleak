from typing import List

from bleak.backends.bluezdbus.utils import extract_service_handle_from_path
from bleak.backends.service import BleakGATTService
from bleak.backends.bluezdbus.characteristic import BleakGATTCharacteristicBlueZDBus


class BleakGATTServiceBlueZDBus(BleakGATTService):
    """GATT Service implementation for the BlueZ DBus backend"""

    def __init__(self, obj, path):
        super().__init__(obj)
        self.__characteristics = []
        self.__path = path
        self.__handle = extract_service_handle_from_path(path)

    @property
    def uuid(self) -> str:
        """The UUID to this service"""
        return self.obj["UUID"]

    @property
    def handle(self) -> int:
        """The integer handle of this service"""
        return self.__handle

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicBlueZDBus]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicBlueZDBus):
        """Add a :py:class:`~BleakGATTCharacteristicBlueZDBus` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)

    def del_characteristic(self, handle: int):
        """Remove a :py:class:`~BleakGATTCharacteristicBlueZDBus` characteristics from service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        for index, desc in enumerate(self.__characteristics):
            if desc.handle == handle:
                del self.__characteristics[index]
                break
        else:
            raise ValueError(
                "Characteristics {} doesn't exists on service {}".format(
                    handle, self.__handle
                )
            )

    @property
    def path(self):
        """The DBus path. Mostly needed by `bleak`, not by end user"""
        return self.__path
