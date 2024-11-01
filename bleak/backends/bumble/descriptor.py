# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Victor Chavez
from typing import Final

from bumble.gatt_client import CharacteristicProxy, DescriptorProxy

from bleak.backends.descriptor import BleakGATTDescriptor


class BleakGATTDescriptorBumble(BleakGATTDescriptor):
    """GATT Descriptor implementation for Bumble backend."""

    def __init__(self, obj: DescriptorProxy, characteristic: CharacteristicProxy):
        super().__init__(obj)
        self.obj = obj
        self._characteristic: Final = characteristic

    @property
    def characteristic_uuid(self) -> str:
        """UUID for the characteristic that this descriptor belongs to"""
        return str(self._characteristic.uuid)

    @property
    def characteristic_handle(self) -> int:
        """handle for the characteristic that this descriptor belongs to"""
        return self._characteristic.handle

    @property
    def uuid(self) -> str:
        """UUID for this descriptor"""
        return str(self.obj.uuid)

    @property
    def handle(self) -> int:
        """Integer handle for this descriptor"""
        return self.obj.handle
