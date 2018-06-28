# -*- coding: utf-8 -*-
"""
BLE Client for Windows 10 systems.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>
"""

import logging
import asyncio
from asyncio.events import AbstractEventLoop
from functools import wraps
from typing import Callable, Any

from bleak.exc import BleakError, BleakDotNetTaskError
from bleak.backends.client import BaseBleakClient
from bleak.backends.dotnet.discovery import discover
from bleak.backends.dotnet.utils import wrap_Task

# CLR imports
# Import of Bleak CLR->UWP Bridge.
from BleakBridge import Bridge

# Import of other CLR components needed.
from System import Array, Byte
from Windows.Devices.Bluetooth import BluetoothConnectionStatus
from Windows.Devices.Bluetooth.GenericAttributeProfile import (
    GattCharacteristic, GattCommunicationStatus
)
from Windows.Foundation import TypedEventHandler

logger = logging.getLogger(__name__)


class BleakClientDotNet(BaseBleakClient):
    """The .NET Bleak Client."""

    def __init__(self, address: str, loop: AbstractEventLoop=None, **kwargs):
        super(BleakClientDotNet, self).__init__(address, loop, **kwargs)

        # Backend specific. Python.NET objects.
        self._device_info = None
        self._requester = None
        self._bridge = Bridge()

    def __str__(self):
        return "BleakClientDotNet ({0})".format(self.address)

    # Connectivity methods

    async def connect(self) -> bool:
        """Connect the BleakClient to the BLE device.

        Returns:
            Boolean from :meth:`~is_connected`.

        """
        # Try to find the desired device.
        devices = await discover(2.0, loop=self.loop)
        sought_device = list(filter(lambda x: x.address.upper() == self.address.upper(), devices))

        if len(sought_device):
            self._device_info = sought_device[0].details
        else:
            raise BleakError(
                "Device with address {0} was " "not found.".format(self.address)
            )

        logger.debug("Connecting to BLE device @ {0}".format(self.address))
        self._requester = await wrap_Task(
            self._bridge.BluetoothLEDeviceFromIdAsync(self._device_info.Id),
            loop=self.loop,
        )

        def _ConnectionStatusChanged_Handler(sender, args):
            logger.debug("_ConnectionStatusChanged_Handler: " + args.ToString())

        self._requester.ConnectionStatusChanged += _ConnectionStatusChanged_Handler

        # Obtain services, which also leads to connection being established.
        await self.get_services()
        await asyncio.sleep(0.2, loop=self.loop)
        connected = await self.is_connected()
        if connected:
            logger.debug("Connection successful.")
        else:
            raise BleakError(
                "Connection to {0} was not successful!".format(self.address)
            )

        return connected

    async def disconnect(self) -> bool:
        logger.debug("Disconnecting from BLE device...")
        # Remove notifications
        # TODO: Make sure all notifications are removed prior to Dispose.
        # Dispose all components that we have requested and created.
        for service_uuid, service in self.services.items():
            service.Dispose()
        self.services = None
        self._requester.Dispose()
        self._requester = None

        return not await self.is_connected()

    async def is_connected(self) -> bool:
        if self._requester:
            return self._requester.ConnectionStatus == BluetoothConnectionStatus.Connected

        else:
            return False

    # GATT services methods

    async def get_services(self) -> dict:
        # Return a list of all services for the device.
        if self.services:
            return self.services
        else:
            logger.debug("Get Services...")
            services = await wrap_Task(
                self._bridge.GetGattServicesAsync(self._requester), loop=self.loop
            )
            if services.Status == GattCommunicationStatus.Success:
                self.services = {s.Uuid.ToString(): s for s in services.Services}
            else:
                raise BleakDotNetTaskError("Could not get GATT services.")

            # TODO: Could this be sped up?
            await asyncio.gather(
                *[
                    asyncio.ensure_future(self._get_chars(service), loop=self.loop)
                    for service_uuid, service in self.services.items()
                ]
            )
            self._services_resolved = True
            return self.services

    async def _get_chars(self, service: Any):
        """Get characteristics for a service

        Args:
            service: The .NET service object.

        """
        logger.debug("Get Characteristics for {0}...".format(service.Uuid.ToString()))
        char_results = await wrap_Task(
            self._bridge.GetCharacteristicsAsync(service), loop=self.loop
        )

        if char_results.Status != GattCommunicationStatus.Success:
            logger.warning(
                "Could not fetch characteristics for {0}: {1}",
                service.Uuid.ToString(),
                char_results.Status,
            )
        else:
            for characteristic in char_results.Characteristics:
                self.characteristics[characteristic.Uuid.ToString()] = characteristic

    # I/O methods

    async def read_gatt_char(self, _uuid: str) -> bytearray:
        """Perform read operation on the specified characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to start notification on.

        Returns:
            (bytearray) The read data.

        """
        characteristic = self.characteristics.get(str(_uuid))
        if not characteristic:
            raise BleakError("Characteristic {0} was not found!".format(_uuid))

        read_results = await wrap_Task(
            self._bridge.ReadCharacteristicValueAsync(characteristic), loop=self.loop
        )
        status, value = read_results.Item1, bytearray(read_results.Item2)
        if status == GattCommunicationStatus.Success:
            logger.debug("Read Characteristic {0} : {1}".format(_uuid, value))
        else:
            raise BleakError(
                "Could not read characteristic value for {0}: {1}",
                characteristic.Uuid.ToString(),
                status,
            )

        return value

    async def write_gatt_char(
        self,
        _uuid: str,
        data: bytearray,
        response: bool = False
    ) -> Any:
        """Perform a write operation of the specified characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to start notification on.
            data (bytes or bytearray): The data to send.
            response (bool): If write response is desired.

        """
        characteristic = self.characteristics.get(str(_uuid))
        if not characteristic:
            raise BleakError("Characteristic {0} was not found!".format(_uuid))

        write_results = await wrap_Task(
            self._bridge.WriteCharacteristicValueAsync(
                characteristic, data, response
            ),
            loop=self.loop,
        )
        if write_results == GattCommunicationStatus.Success:
            logger.debug("Write Characteristic {0} : {1}".format(_uuid, data))
        else:
            raise BleakError(
                "Could not write value {0} to characteristic {1}: {2}",
                data,
                characteristic.Uuid.ToString(),
                write_results,
            )

    async def start_notify(
        self,
        _uuid: str,
        callback: Callable[[str, Any], Any],
        **kwargs
    ) -> None:
        """Activate notifications on a characteristic.

        Callbacks must accept two inputs. The first will be a uuid string
        object and the second will be a bytearray.

        .. code-block:: python

            def callback(sender, data):
                print(f"{sender}: {data}")
            client.start_notify(char_uuid, callback)

        Args:
            _uuid (str or UUID): The uuid of the characteristics to start notification on.
            callback (function): The function to be called on notification.

        """
        characteristic = self.characteristics.get(str(_uuid))

        if self._notification_callbacks.get(str(_uuid)):
            await self.stop_notify(_uuid)

        dotnet_callback = TypedEventHandler[GattCharacteristic, Array[Byte]](
            _notification_wrapper(callback)
        )
        status = await wrap_Task(
            self._bridge.StartNotify(characteristic, dotnet_callback), loop=self.loop
        )
        if status != GattCommunicationStatus.Success:
            raise BleakError(
                "Could not start notify on {0}: {1}",
                characteristic.Uuid.ToString(),
                status,
            )

    async def stop_notify(self, _uuid: str) -> None:
        """Deactivate notification on a specified characteristic.

        Args:
            _uuid: The characteristic to stop notifying on.

        """
        characteristic = self.characteristics.get(str(_uuid))
        status = await wrap_Task(
            self._bridge.StopNotify(characteristic), loop=self.loop
        )
        if status != GattCommunicationStatus.Success:
            raise BleakError(
                "Could not start notify on {0}: {1}",
                characteristic.Uuid.ToString(),
                status,
            )


def _notification_wrapper(func: Callable):
    @wraps(func)
    def dotnet_notification_parser(sender: Any, data: Any):
        # Return only the UUID string representation as sender.
        # Also do a conversion from System.Bytes[] to bytearray.
        return func(sender.Uuid.ToString(), bytearray(data))

    return dotnet_notification_parser
