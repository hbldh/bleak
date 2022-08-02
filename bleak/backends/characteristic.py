# -*- coding: utf-8 -*-
"""
Interface class for the Bleak representation of a GATT Characteristic

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
import enum
from uuid import UUID
from typing import List, Union, Any

from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.uuids import uuidstr_to_str
from bleak import abstract_api


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


class BleakGATTCharacteristic(abstract_api.BleakGATTCharacteristic):
    """Interface for the Bleak representation of a GATT Characteristic"""

    @abc.abstractmethod
    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        """Add a :py:class:`~BleakGATTDescriptor` to the characteristic.

        Should not be used by end user, but rather by `bleak` itself.
        """
        raise NotImplementedError()
