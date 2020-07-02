# -*- coding: utf-8 -*-
"""
Gatt Service Collection class and interface class for the Bleak representation of a GATT Service.

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
import uuid
from uuid import UUID
from typing import List, Union, Iterator

from bleak import BleakError
from bleak.uuids import uuidstr_to_str
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor


class BleakGATTService(abc.ABC):
    """Interface for the Bleak representation of a GATT Service."""

    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return "{0}: {1}".format(self.uuid, self.description)

    @property
    @abc.abstractmethod
    def uuid(self) -> str:
        """The UUID to this service"""
        raise NotImplementedError()

    @property
    def description(self) -> str:
        """String description for this service"""
        return uuidstr_to_str(self.uuid)

    @property
    @abc.abstractmethod
    def characteristics(self) -> List[BleakGATTCharacteristic]:
        """List of characteristics for this service"""
        raise NotImplementedError()

    @abc.abstractmethod
    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        """Add a :py:class:`~BleakGATTCharacteristic` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_characteristic(
        self, _uuid: Union[str, UUID]
    ) -> Union[BleakGATTCharacteristic, None]:
        """Get a characteristic by UUID"""
        raise NotImplementedError()


class BleakGATTServiceCollection(object):
    """Simple data container for storing the peripheral's service complement."""

    def __init__(self):
        self.__services = {}
        self.__characteristics = {}
        self.__descriptors = {}

    def __getitem__(
        self, item: Union[str, int, uuid.UUID]
    ) -> Union[BleakGATTService, BleakGATTCharacteristic, BleakGATTDescriptor]:
        """Get a service, characteristic or descriptor from uuid or handle"""
        return self.services.get(
            str(item), self.characteristics.get(item, self.descriptors.get(item, None))
        )

    def __iter__(self) -> Iterator[BleakGATTService]:
        """Returns an iterator over all BleakGATTService objects"""
        return iter(self.services.values())

    @property
    def services(self) -> dict:
        """Returns dictionary of UUID strings to BleakGATTService"""
        return self.__services

    @property
    def characteristics(self) -> dict:
        """Returns dictionary of handles to BleakGATTCharacteristic"""
        return self.__characteristics

    @property
    def descriptors(self) -> dict:
        """Returns a dictionary of integer handles to BleakGATTDescriptor"""
        return self.__descriptors

    def add_service(self, service: BleakGATTService):
        """Add a :py:class:`~BleakGATTService` to the service collection.

        Should not be used by end user, but rather by `bleak` itself.
        """
        if service.uuid not in self.__services:
            self.__services[service.uuid] = service
        else:
            raise BleakError(
                "This service is already present in this BleakGATTServiceCollection!"
            )

    def get_service(self, _uuid: Union[str, UUID]) -> BleakGATTService:
        """Get a service by UUID string"""
        return self.services.get(str(_uuid), None)

    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        """Add a :py:class:`~BleakGATTCharacteristic` to the service collection.

        Should not be used by end user, but rather by `bleak` itself.
        """
        if characteristic.handle not in self.__characteristics:
            self.__characteristics[characteristic.handle] = characteristic
            self.__services[characteristic.service_uuid].add_characteristic(
                characteristic
            )
        else:
            raise BleakError(
                "This characteristic is already present in this BleakGATTServiceCollection!"
            )

    def get_characteristic(
        self, specifier: Union[int, str, UUID]
    ) -> BleakGATTCharacteristic:
        """Get a characteristic by handle (int) or UUID (str or uuid.UUID)"""
        if isinstance(specifier, int):
            return self.characteristics.get(specifier, None)
        else:
            # Assume uuid usage.
            x = list(
                filter(
                    lambda x: x.uuid == str(specifier), self.characteristics.values()
                )
            )
            if len(x) > 1:
                raise BleakError(
                    "Multiple Characteristics with this UUID, refer to your desired characteristic by the `handle` attribute instead."
                )
            else:
                return x[0] if x else None

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        """Add a :py:class:`~BleakGATTDescriptor` to the service collection.

         Should not be used by end user, but rather by `bleak` itself.
         """
        if descriptor.handle not in self.__descriptors:
            self.__descriptors[descriptor.handle] = descriptor
            self.__characteristics[descriptor.characteristic_handle].add_descriptor(
                descriptor
            )
        else:
            raise BleakError(
                "This descriptor is already present in this BleakGATTServiceCollection!"
            )

    def get_descriptor(self, handle: int) -> BleakGATTDescriptor:
        """Get a descriptor by integer handle"""
        return self.descriptors.get(handle, None)
