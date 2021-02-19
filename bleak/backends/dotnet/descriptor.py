# -*- coding: utf-8 -*-
from bleak.backends.descriptor import BleakGATTDescriptor

# Import of BleakBridge to enable loading of winrt bindings
from BleakBridge import Bridge  # noqa: F401

from Windows.Devices.Bluetooth.GenericAttributeProfile import GattDescriptor


class BleakGATTDescriptorDotNet(BleakGATTDescriptor):
    """GATT Descriptor implementation for .NET backend"""

    def __init__(
        self, obj: GattDescriptor, characteristic_uuid: str, characteristic_handle: int
    ):
        super(BleakGATTDescriptorDotNet, self).__init__(obj)
        self.obj = obj
        self.__characteristic_uuid = characteristic_uuid
        self.__characteristic_handle = characteristic_handle

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
        return self.obj.Uuid.ToString()

    @property
    def handle(self) -> int:
        """Integer handle for this descriptor"""
        return self.obj.AttributeHandle
