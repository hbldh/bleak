"""
BLE Client for CoreBluetooth on macOS

Created on 2019-6-26 by kevincar <kevincarrolldavis@gmail.com>
"""

import logging
import asyncio

from typing import Callable, Any

from Foundation import NSData, CBUUID

from asyncio.events import AbstractEventLoop
from bleak.exc import BleakError

from ..corebluetooth import CBAPP as cbapp
from bleak.backends.corebluetooth.discovery import discover
from bleak.backends.client import BaseBleakClient
from bleak.backends.service import BleakGATTServiceCollection

from bleak.backends.corebluetooth.service import BleakGATTServiceCoreBluetooth
from bleak.backends.corebluetooth.characteristic import BleakGATTCharacteristicCoreBluetooth
from bleak.backends.corebluetooth.descriptor import BleakGATTDescriptorCoreBluetooth

logger = logging.getLogger(__name__)

class BleakClientCoreBluetooth(BaseBleakClient):
    """
    CoreBluetooth class interface for BleakClient
    """

    def __init__(self, address: str, loop: AbstractEventLoop, **kwargs):
        super(BleakClientCoreBluetooth, self).__init__(address, loop, **kwargs)

        self._device_info = None
        self._requester = None
        self._callbacks = {}
        self._services = None

    def __str__(self):
        return "BleakClientCoreBluetooth ({})".format(self.address)

    async def connect(self) -> bool:
        """
        Connect to a specified Peripheral
        """

        devices = await discover(10.0, loop=self.loop)
        sought_device = list(filter(lambda x: x.address.upper() == self.address.upper(), devices))

        if len(sought_device):
            self._device_info = sought_device[0].details
        else:
            raise BleakError("Device with address {} was not found").format(self.address)

        logger.debug("Connecting to BLE device @ {}").format(self.address)

        await cbapp.central_manager_delegate.connect_(sought_device[0].details)
        
        # Now get services
        await self.get_services()

        return True

    async def disconnect(self) -> bool:
        """Disconnect from the peripheral device"""
        await cbapp.central_manager_delegate.disconnect()
        return True

    async def is_connected(self) -> bool:
        """Checks for current active connection"""
        return cbapp.central_manager_delegate.isConnected

    async def get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self._services != None:
            return self._services

        logger.debug("retreiving services...")
        services = await cbapp.central_manager_delegate.connected_peripheral_delegate.discoverServices()

        for service in services:
            serviceUUID = service.UUID().UUIDString()
            logger.debug("retreiving characteristics for service {}").format(serviceUUID)
            characteristics = await cbapp.central_manager_delegate.connected_peripheral_delegate.discoverCharacteristics_(service)

            self.services.add_service(BleakGATTServiceCoreBluetooth(service))

            for characteristic in characteristics:
                cUUID = characteristic.UUID().UUIDString()
                logger.debug("retreiving descriptors for characteristic {}").format(cUUID)
                descriptors = await cbapp.central_manager_delegate.connected_peripheral_delegate.discoverDescriptors_(characteristic)

                self.services.add_characteristic(BleakGATTCharacteristicCoreBluetooth(characteristic))
                for descriptor in descriptors:
                    self.services.add_descriptor(
                            BleakGATTDescriptorCoreBluetooth(
                                descriptor, characteristic.UUID().UUIDString()
                                )
                            )
        self._services_resolved = True
        return self.services

    async def read_gatt_char(self, _uuid: str, use_cached=False, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to read from.
            use_cached (bool): `False` forces macOS to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.

        """
        _uuid = await self.get_appropriate_uuid(_uuid)
        characteristic = self.services.get_characteristic(_uuid)
        if not characteristic:
            raise BleakError("Characteristic {} was not found!").format(_uuid)

        value = await cbapp.central_manager_delegate.connected_peripheral_delegate.readCharacteristic_(characteristic.obj, use_cached=use_cached)
        bytes = value.getBytes_length_(None, len(value))
        return bytearray(bytes)

    async def read_gatt_descriptor(self, handle: int, use_chased=False, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            use_cached (bool): `False` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.
        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor {} was not found!".format(handle))

        value = await cbapp.central_manager_delegate.connected_peripheral_delegate.readDescriptor_(descriptor.obj, use_cached=use_cached)
        bytes = value.getBytes_length_(None, len(value))
        return bytearray(bytes)

    async def write_gatt_char(self, _uuid: str, data: bytearray, response: bool = False) -> None:
        raise BleakError("BleakClientCoreBluetooth:write_gatt_char not implemented")

    async def write_gatt_descriptor(self, handle: int, data: bytearray) -> None:
        raise BleakError("BleakClientCoreBluetooth:write_gatt_descriptor not implemented")

    async def start_notify(self, _uuid: str, callback: Callable[[str, Any], Any], **kwargs) -> None:
        raise BleakError("BleakClientCoreBluetooth:start_notify not implemented")

    # async def _start_notify( self, characteristic_obj: GattCharacteristic, callback: Callable[[str, Any], Any]):
        # raise BleakError("BleakClientCoreBluetooth:_start_notify not implemented")

    async def stop_notify(self, _uuid: str) -> None:
        raise BleakError("BleakClientCoreBluetooth:stop_notify not implemented")

    async def get_appropriate_uuid(self, _uuid: str) -> str:
        if len(_uuid) == 4:
            return _uuid.upper()

        if await self.is_uuid_16bit_compatible(_uuid):
            return _uuid[4:8].upper()

        return _uuid.upper()

    async def is_uuid_16bit_compatible(self, _uuid: str) -> bool:
        test_uuid = "0000FFFF-0000-1000-8000-00805F9B34FB"
        test_int = await self.convert_uuid_to_int(test_uuid)
        uuid_int = await self.convert_uuid_to_int(_uuid)
        result_int = uuid_int & test_int
        return uuid_int == result_int

    async def convert_uuid_to_int(self, _uuid: str) -> int:
        UUID_cb = CBUUID.alloc().initWithString_(_uuid)
        UUID_data = UUID_cb.data()
        UUID_bytes = UUID_data.getBytes_length_(None, len(UUID_data))
        UUID_int = int.from_bytes(UUID_bytes, byteorder='big')
        return UUID_int

    async def convert_int_to_uuid(self, i: int) -> str:
        UUID_bytes = i.to_bytes(length=16, byteorder='big')
        UUID_data = NSData.alloc().initWithBytes_length_(UUID_bytes, len(UUID_bytes))
        UUID_cb = CBUUID.alloc().initWithData_(UUID_data)
        return UUID_cb.UUIDString()
