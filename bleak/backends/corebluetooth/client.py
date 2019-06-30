"""
BLE Client for CoreBluetooth on macOS

Created on 2019-6-26 by kevincar <kevincarrolldavis@gmail.com>
"""

import logging
import asyncio

from typing import Callable, Any

from asyncio.events import AbstractEventLoop
from bleak.exc import BleakError

from ..corebluetooth import CBAPP as cbapp
from bleak.backends.corebluetooth.discovery import discover
from bleak.backends.client import BaseBleakClient
from bleak.backends.service import BleakGATTServiceCollection

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
        return f"BleakClientCoreBluetooth ({self.address})"

    async def connect(self) -> bool:
        """
        Connect to a specified Peripheral
        """

        devices = await discover(10.0, loop=self.loop)
        sought_device = list(filter(lambda x: x.address.upper() == self.address.upper(), devices))

        if len(sought_device):
            self._device_info = sought_device[0].details
        else:
            raise BleakError(f"Device with address {self.address} was not found")

        logger.debug(f"Connecting to BLE device @ {self.address}")

        await cbapp.central_manager_delegate.connect_(sought_device[0].details)
        
        # Now get services
        await self.get_services()

    async def disconnect(self) -> bool:
        raise BleakError("BleakClientCoreBluetooth:disconnect not implemented")

    async def is_connected(self) -> bool:
        raise BleakError("BleakClientCoreBluetooth:is_connected not implmeneted")

    async def get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self._services != None:
            return self._services

        logger.debug("retreiving services...")
        services = await cbapp.central_manager_delegate.connected_peripheral_delegate.discoverServices()

        logger.debug(f"retreived {len(services)} services")

        raise BleakError("BleakClientCoreBluetooth:get_services not implemented")

    async def read_gatt_char(self, _uuid: str, use_cached=False, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to read from.
            use_cached (bool): `False` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.

        """
        raise BleakError("BleakClientCoreBluetooth:read_gatt_char not implemented")

    async def read_gatt_descriptor(self, handle: int, use_chased=False, **kwargs) -> bytearray:

        raise BleakError("BleakClientCoreBluetooth:read_gatt_descriptor not implemented")

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
