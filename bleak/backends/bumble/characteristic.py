# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Victor Chavez

from typing import Callable, Final, List, Union
from uuid import UUID

from bumble.gatt import Characteristic
from bumble.gatt_client import CharacteristicProxy, ServiceProxy

from bleak import normalize_uuid_str
from bleak.backends.bumble.utils import bumble_uuid_to_str
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor


class BleakGATTCharacteristicBumble(BleakGATTCharacteristic):
    """GATT Characteristic implementation for the Bumble backend."""

    def __init__(
        self,
        obj: CharacteristicProxy,
        max_write_without_response_size: Callable[[], int],
        svc: ServiceProxy,
    ):
        super().__init__(obj, max_write_without_response_size)
        self.__descriptors: List[BleakGATTDescriptor] = []
        props = [flag for flag in Characteristic.Properties if flag in obj.properties]
        self.__props: Final = [str(prop) for prop in props]
        self.__svc: Final = svc
        uuid = bumble_uuid_to_str(obj.uuid)
        self.__uuid: Final = normalize_uuid_str(uuid)

    @property
    def service_uuid(self) -> str:
        """The uuid of the Service containing this characteristic"""
        return bumble_uuid_to_str(self.__svc.uuid)

    @property
    def service_handle(self) -> int:
        """The integer handle of the Service containing this characteristic"""
        return self.__svc.handle

    @property
    def handle(self) -> int:
        """The handle of this characteristic"""
        return int(self.obj.handle)

    @property
    def uuid(self) -> str:
        """The uuid of this characteristic"""
        return self.__uuid

    @property
    def properties(self) -> List[str]:
        """Properties of this characteristic"""
        return self.__props

    @property
    def descriptors(self) -> List[BleakGATTDescriptor]:
        """List of descriptors for this characteristic"""
        return self.__descriptors

    def get_descriptor(
        self, specifier: Union[int, str, UUID]
    ) -> Union[BleakGATTDescriptor, None]:
        """Get a descriptor by handle (int) or UUID (str or uuid.UUID)"""
        try:
            if isinstance(specifier, int):
                return next(filter(lambda x: x.handle == specifier, self.descriptors))
            else:
                return next(
                    filter(lambda x: x.uuid == str(specifier), self.descriptors)
                )
        except StopIteration:
            return None

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        """Add a :py:class:`~BleakGATTDescriptor` to the characteristic.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__descriptors.append(descriptor)
