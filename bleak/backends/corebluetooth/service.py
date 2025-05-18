import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

from CoreBluetooth import CBService

from bleak.backends.corebluetooth.characteristic import (
    BleakGATTCharacteristicCoreBluetooth,
)
from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from bleak.backends.service import BleakGATTService


class BleakGATTServiceCoreBluetooth(BleakGATTService):
    """GATT Characteristic implementation for the CoreBluetooth backend"""

    def __init__(self, obj: CBService):
        super().__init__(obj)
        self.__characteristics: list[BleakGATTCharacteristicCoreBluetooth] = []
        # N.B. the `startHandle` method of the CBService is an undocumented Core Bluetooth feature,
        # which Bleak takes advantage of in order to have a service handle to use.
        self.__handle: int = int(self.obj.startHandle())

    @property
    def handle(self) -> int:
        """The integer handle of this service"""
        return self.__handle

    @property
    def uuid(self) -> str:
        """UUID for this service."""
        return cb_uuid_to_str(self.obj.UUID())

    @property
    def characteristics(self) -> list[BleakGATTCharacteristicCoreBluetooth]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(
        self, characteristic: BleakGATTCharacteristicCoreBluetooth
    ) -> None:
        """Add a :py:class:`~BleakGATTCharacteristicCoreBluetooth` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
