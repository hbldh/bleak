from typing import List, Union

from Foundation import CBService, CBUUID

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
    def uuid(self) -> str:
        return self.obj.UUID().UUIDString()

    @property
    def characteristics(self) -> List[BleakGATTCharacteristicCoreBluetooth]:
        """List of characteristics for this service"""
        return self.__characteristics

    def get_characteristic(
        self, _uuid: CBUUID
    ) -> Union[BleakGATTCharacteristicCoreBluetooth, None]:
        """Get a characteristic by UUID"""
        try:
            return next(filter(lambda x: x.uuid == _uuid, self.characteristics))
        except StopIteration:
            return None

    def add_characteristic(self, characteristic: BleakGATTCharacteristicCoreBluetooth):
        """Add a :py:class:`~BleakGATTCharacteristicDotNet` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
