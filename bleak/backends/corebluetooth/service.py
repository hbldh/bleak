from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from typing import List

from Foundation import CBService

from bleak.backends.corebluetooth.characteristic import (
    BleakGATTCharacteristicCoreBluetooth,
)
from bleak.backends.service import BleakGATTService


class BleakGATTServiceCoreBluetooth(BleakGATTService):
    """GATT Characteristic implementation for the CoreBluetooth backend"""

    def __init__(self, obj: CBService):
        super().__init__(obj)
        self.__characteristics = []

    @property
    def handle(self) -> str:
        """The integer handle of this service"""
        raise NotImplementedError("This needs to be implemented!")

    @property
    def uuid(self) -> str:
        """UUID for this service."""
        return cb_uuid_to_str(self.obj.UUID())

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicCoreBluetooth]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristicCoreBluetooth):
        """Add a :py:class:`~BleakGATTCharacteristicDotNet` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
