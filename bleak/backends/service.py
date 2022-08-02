# -*- coding: utf-8 -*-
"""
Gatt Service Collection class and interface class for the Bleak representation of a GATT Service.

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
from uuid import UUID
from typing import Dict, List, Optional, Union, Iterator
import logging

from bleak import BleakError
from bleak.uuids import uuidstr_to_str
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak import abstract_api

logger = logging.getLogger(__name__)


class BleakGATTService(abstract_api.BleakGATTService):
    """Interface for the Bleak representation of a GATT Service.

    Interface for backend implementors.
    """

    @abc.abstractmethod
    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        """Add a :py:class:`~BleakGATTCharacteristic` to the service.

        Should not be used by end user, but rather by `bleak` itself.
        """
        raise NotImplementedError()


class BleakGATTServiceCollection(abstract_api.BleakGATTServiceCollection):
    """Simple data container for storing the peripheral's service complement."""

    def add_service(self, service: BleakGATTService):
        """Add a :py:class:`~BleakGATTService` to the service collection.

        Should not be used by end user, but rather by `bleak` itself.
        """
        if service.handle not in self._services:
            self._services[service.handle] = service
        else:
            logger.error(
                "The service '%s' is already present in this BleakGATTServiceCollection!",
                service.handle,
            )

    def add_characteristic(self, characteristic: BleakGATTCharacteristic):
        """Add a :py:class:`~BleakGATTCharacteristic` to the service collection.

        Should not be used by end user, but rather by `bleak` itself.
        """
        if characteristic.handle not in self._characteristics:
            self._characteristics[characteristic.handle] = characteristic
            self._services[characteristic.service_handle].add_characteristic(
                characteristic
            )
        else:
            logger.error(
                "The characteristic '%s' is already present in this BleakGATTServiceCollection!",
                characteristic.handle,
            )

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        """Add a :py:class:`~BleakGATTDescriptor` to the service collection.

        Should not be used by end user, but rather by `bleak` itself.
        """
        if descriptor.handle not in self._descriptors:
            self._descriptors[descriptor.handle] = descriptor
            self._characteristics[descriptor.characteristic_handle].add_descriptor(
                descriptor
            )
        else:
            logger.error(
                "The descriptor '%s' is already present in this BleakGATTServiceCollection!",
                descriptor.handle,
            )
