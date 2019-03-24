# -*- coding: utf-8 -*-
"""
Gatt Service Collection class and interface class for the Bleak representation of a GATT Service.

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
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
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def description(self) -> str:
        return uuidstr_to_str(self.uuid)

    @property
    @abc.abstractmethod
    def characteristics(self) -> List[BleakGATTCharacteristic]:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_characteristic(self, _uuid) -> Union[BleakGATTCharacteristic, None]:
        raise NotImplementedError()


class BleakGATTServiceCollection(object):
    """Simple data container for storing the peripheral's service complement."""

    def __init__(self):
        self.__services = {}
        self.__characteristics = {}
        self.__descriptors = {}

    def __getitem__(
        self, item
    ) -> Union[BleakGATTService, BleakGATTCharacteristic, BleakGATTDescriptor]:
        """Get a service, charactersitic or descriptor from uuid."""
        return self.services.get(
            item, self.characteristics.get(item, self.descriptors.get(item, None))
        )

    def __iter__(self) -> Iterator[BleakGATTService]:
        return iter(self.services.values())

    @property
    def services(self) -> dict:
        return self.__services

    @property
    def characteristics(self) -> dict:
        return self.__characteristics

    @property
    def descriptors(self) -> dict:
        return self.__descriptors

    def add_service(self, service: BleakGATTService):
        if service.uuid not in self.__services:
            self.__services[service.uuid] = service
        else:
            raise BleakError(
                "This service is already present in this BleakGATTServiceCollection!"
            )

    def get_service(self, _uuid) -> BleakGATTService:
        return self.services.get(_uuid, None)

    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        if characteristic.uuid not in self.__characteristics:
            self.__characteristics[characteristic.uuid] = characteristic
            self.__services[characteristic.service_uuid].add_characteristic(
                characteristic
            )
        else:
            raise BleakError(
                "This characteristic is already present in this BleakGATTServiceCollection!"
            )

    def get_characteristic(self, _uuid) -> BleakGATTCharacteristic:
        return self.characteristics.get(_uuid, None)

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        if descriptor.handle not in self.__descriptors:
            self.__descriptors[descriptor.handle] = descriptor
            self.__characteristics[descriptor.characteristic_uuid].add_descriptor(
                descriptor
            )
        else:
            raise BleakError(
                "This descriptor is already present in this BleakGATTServiceCollection!"
            )

    def get_descriptor(self, handle) -> BleakGATTDescriptor:
        return self.descriptors.get(handle, None)
