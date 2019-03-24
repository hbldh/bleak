# -*- coding: utf-8 -*-
"""
Interface class for the Bleak representation of a GATT Descriptor

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
from bleak.backends.descriptor import BleakGATTDescriptor

from Windows.Devices.Bluetooth.GenericAttributeProfile import GattDescriptor


class BleakGATTDescriptorDotNet(BleakGATTDescriptor):
    """Interface for the Bleak representation of a GATT Descriptor"""

    def __init__(self, obj: GattDescriptor, characteristic_uuid: str):
        super(BleakGATTDescriptorDotNet, self).__init__(obj)
        self.obj = obj
        self.__characteristic_uuid = characteristic_uuid

    def __str__(self):
        return "{0}: (Handle: {1})".format(self.uuid, self.handle)

    @property
    def characteristic_uuid(self):
        return self.__characteristic_uuid

    @property
    def uuid(self):
        return self.obj.Uuid.ToString()

    @property
    def handle(self):
        return self.obj.AttributeHandle
