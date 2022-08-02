# -*- coding: utf-8 -*-

from bleak_winrt.windows.devices.bluetooth.genericattributeprofile import GattDescriptor

from bleak.backends.descriptor import BleakGATTDescriptor


class BleakGATTDescriptorWinRT(BleakGATTDescriptor):
    """GATT Descriptor implementation for .NET backend, implemented with WinRT"""

    def __init__(
        self, obj: GattDescriptor, characteristic_uuid: str, characteristic_handle: int
    ):
        """Should not be called by end user, only by bleak itself"""
        super(BleakGATTDescriptorWinRT, self).__init__(obj)
        self.obj = obj
        self.__characteristic_uuid = characteristic_uuid
        self.__characteristic_handle = characteristic_handle

    @property
    def characteristic_handle(self) -> int:
        return self.__characteristic_handle

    @property
    def characteristic_uuid(self) -> str:
        return self.__characteristic_uuid

    @property
    def uuid(self) -> str:
        return str(self.obj.uuid)

    @property
    def handle(self) -> int:
        return self.obj.attribute_handle
