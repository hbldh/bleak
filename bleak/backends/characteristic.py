# -*- coding: utf-8 -*-
"""
Interface class for the Bleak representation of a GATT Characteristic

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
from typing import List, Union, Any
import enum

from bleak.backends.descriptor import BleakGATTDescriptor


class GattCharacteristicsFlags(enum.Enum):
    broadcast = 0x0001
    read = 0x0002
    write_without_response = 0x0004
    write = 0x0008
    notify = 0x0010
    indicate = 0x0020
    authenticated_signed_writes = 0x0040
    extended_properties = 0x0080
    reliable_write = 0x0100
    writable_auxiliaries = 0x0200


class BleakGATTCharacteristic(abc.ABC):
    """Interface for the Bleak representation of a GATT Characteristic

    """

    def __init__(self, obj: Any):
        self.obj = obj

    def __str__(self):
        return "{0}: {1}".format(self.uuid, self.description)

    @property
    @abc.abstractmethod
    def service_uuid(self) -> str:
        """The UUID of the Service containing this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def uuid(self) -> str:
        """The UUID for this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Description for this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def properties(self) -> List[str]:
        """Properties of this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def descriptors(self) -> List:
        """List of descriptors for this service"""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_descriptor(self, _uuid: str) -> Union[BleakGATTDescriptor, None]:
        """Get a descriptor by UUID"""
        raise NotImplementedError()

    @abc.abstractmethod
    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        """Add a :py:class:`~BleakGATTDescriptor` to the characteristic.

        Should not be used by end user, but rather by `bleak` itself.
        """
        raise NotImplementedError()
