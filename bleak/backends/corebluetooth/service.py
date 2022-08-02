from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from typing import List

from CoreBluetooth import CBService

from bleak.backends.corebluetooth.characteristic import (
    BleakGATTCharacteristicCoreBluetooth,
)
from bleak.backends.service import BleakGATTService


class BleakGATTServiceCoreBluetooth(BleakGATTService):
    """GATT Service implementation for the CoreBluetooth backend"""

    def __init__(self, obj: CBService):
        """Should not be called by end user, only by bleak itself"""
        super().__init__(obj)
        self.__characteristics: List[BleakGATTCharacteristicCoreBluetooth] = []
        # N.B. the `startHandle` method of the CBService is an undocumented Core Bluetooth feature,
        # which Bleak takes advantage of in order to have a service handle to use.
        self.__handle: int = int(self.obj.startHandle())

    @property
    def handle(self) -> int:
        return self.__handle

    @property
    def uuid(self) -> str:
        return cb_uuid_to_str(self.obj.UUID())

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicCoreBluetooth]:
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicCoreBluetooth):
        self.__characteristics.append(characteristic)
