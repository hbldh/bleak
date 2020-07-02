"""
Interface class for the Bleak representation of a GATT Descriptor

Created on 2019-06-28 by kevincar <kevincarrolldavis@gmail.com>

"""
from Foundation import CBDescriptor

from bleak.backends.descriptor import BleakGATTDescriptor


class BleakGATTDescriptorCoreBluetooth(BleakGATTDescriptor):
    """GATT Descriptor implementation for CoreBluetooth backend"""

    def __init__(
        self, obj: CBDescriptor, characteristic_uuid: str, characteristic_handle: int
    ):
        super(BleakGATTDescriptorCoreBluetooth, self).__init__(obj)
        self.obj = obj
        self.__characteristic_uuid = characteristic_uuid
        self.__characteristic_handle = characteristic_handle

    def __str__(self):
        return "{0}: (Handle: {1})".format(self.uuid, self.handle)

    @property
    def characteristic_handle(self) -> int:
        """handle for the characteristic that this descriptor belongs to"""
        return self.__characteristic_handle

    @property
    def characteristic_uuid(self) -> str:
        """UUID for the characteristic that this descriptor belongs to"""
        return self.__characteristic_uuid

    @property
    def uuid(self) -> str:
        """UUID for this descriptor"""
        return self.obj.UUID().UUIDString()

    @property
    def handle(self) -> int:
        """Integer handle for this descriptor"""
        return int(self.obj.handle())
