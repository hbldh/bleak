# -*- coding: utf-8 -*-
"""
Interface class for the Bleak representation of a GATT Characteristic

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
from typing import List, Union, Any

from bleak.backends.descriptor import BleakGATTDescriptor


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
        """The uuid of the Service containing this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def uuid(self) -> str:
        """The uuid of this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def description(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def properties(self) -> List:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def descriptors(self) -> List:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_descriptor(self, _uuid: str) -> Union[BleakGATTDescriptor, None]:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        raise NotImplementedError()
