# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Victor Chavez

from typing import Final, List

from bumble.gatt_client import ServiceProxy

from bleak import BleakGATTCharacteristic, normalize_uuid_str
from bleak.backends.bumble.utils import bumble_uuid_to_str
from bleak.backends.service import BleakGATTService


class BleakGATTServiceBumble(BleakGATTService):
    """GATT Characteristic implementation for the Bumble backend."""

    def __init__(self, obj: ServiceProxy):
        super().__init__(obj)
        self.__characteristics: List[BleakGATTCharacteristic] = []
        uuid = bumble_uuid_to_str(obj.uuid)
        self.__uuid: Final = normalize_uuid_str(uuid)

    @property
    def handle(self) -> int:
        return self.obj.handle

    @property
    def uuid(self) -> str:
        return self.__uuid

    @property
    def characteristics(self) -> List[BleakGATTCharacteristic]:
        """List of characteristics for this service"""
        return self.__characteristics

    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        """Add a :py:class:`~BleakGATTCharacteristicWinRT` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__characteristics.append(characteristic)
