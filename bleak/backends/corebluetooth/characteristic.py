"""
Interface class for the Bleak representation of a GATT Characteristic

Created on 2019-06-28 by kevincar <kevincarrolldavis@gmail.com>

"""
from typing import List, Union
from enum import Enum

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.corebluetooth.descriptor import BleakGATTDescriptorCoreBluetooth

from Foundation import CBCharacteristic

class CBChacteristicProperties(Enum):
    BROADCAST = 0x1
    READ = 0x2
    WRITE_WIHTOUT_RESPONSE = 0x4
    WRITE = 0x8
    NOTIFY = 0x10
    INDICATE = 0x20
    AUTHENTICATED_SIGNED_WRITES = 0x40
    EXTENDED_PROPERTIES = 0x80
    NOTIFY_ENCRYPTION_REQUIRED = 0x100
    INDICATE_ENCRYPTION_REQUIRED = 0x200


class BleakGATTCharacteristicDotNet(BleakGATTCharacteristic):
    """GATT Characteristic implementation for the CoreBluetooth backend"""

    def __init__(self, obj: CBCharacteristic):
        super().__init__(obj)
        self.__descriptors = []
        self.__props = obj.properties

    def __str__(self):
        return "{0}: {1}".format(self.uuid, self.description)

    @property
    def service_uuid(self) -> str:
        """The uuid of the Service containing this characteristic"""
        return self.obj.service.UUID.UUIDString()

    @property
    def uuid(self) -> str:
        """The uuid of this characteristic"""
        return self.obj.UUID.UUIDString()

    # @property
    # def description(self) -> str:
        # """Description for this characteristic"""
        # return self.obj.UserDescription

    @property
    def properties(self) -> List:
        """Properties of this characteristic"""
        return self.__props

    @property
    def descriptors(self) -> List[BleakGATTDescriptorCoreBluetooth]:
        """List of descriptors for this service"""
        return self.__descriptors

    def get_descriptor(self, _uuid) -> Union[BleakGATTDescriptorCoreBluetooth, None]:
        """Get a descriptor by UUID"""
        try:
            return next(filter(lambda x: x.uuid == _uuid, self.descriptors))
        except StopIteration:
            return None

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        """Add a :py:class:`~BleakGATTDescriptor` to the characteristic.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__descriptors.append(descriptor)
