# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Victor Chavez
"""
BLE Client for Bumble
"""

import logging
import sys
import uuid
import warnings
from functools import partial
from typing import Dict, Optional, Union, Final

from bumble.controller import Controller
from bumble.device import Connection, Device, Peer
from bumble.hci import HCI_REMOTE_USER_TERMINATED_CONNECTION_ERROR
from bumble.host import Host

from bleak.backends.bumble import (
    BumbleTransportCfg,
    get_default_host_mode,
    get_default_transport_cfg,
    get_link,
    start_transport,
)
from bleak.backends.bumble.characteristic import BleakGATTCharacteristicBumble
from bleak.backends.bumble.descriptor import BleakGATTDescriptorBumble
from bleak.backends.bumble.service import BleakGATTServiceBumble
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient, NotifyCallback
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakCharacteristicNotFoundError, BleakError

if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer


logger = logging.getLogger(__name__)


class BleakClientBumble(BaseBleakClient):
    """Bumble class interface for BleakClient

    Args:
        address_or_ble_device: The Bluetooth address of the
            BLE peripheral to connect to or the BLEDevice object representing it.
    Keyword Args:
        cfg: Bumble transport configuration.
        host_mode:
            Set to ``True`` to set bumble as an HCI Host. Useful
            for connecting an external HCI controller
            If ``False`` it will be set as a controller.

    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super().__init__(address_or_ble_device, **kwargs)
        self._peer: Optional[Peer] = None
        self._dev: Optional[Device] = None
        self._connection: Optional[Connection] = None
        self._subs: Dict[int, list[NotifyCallback]] = {}
        self._cfg: Final[BumbleTransportCfg] = kwargs.get("cfg", get_default_transport_cfg())
        self._host_mode: Final[bool] = kwargs.get("host_mode", get_default_host_mode())

    @property
    def mtu_size(self) -> int:
        if not self._connection:
            raise BleakError("Not connected")
        return self._connection.att_mtu

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Returns:
            Boolean representing connection status.

        """
        self._dev = Device("client")
        self._dev.on("connection", self.on_connection)
        self._dev.host = Host()
        if not self._host_mode:
            self._dev.host.controller = Controller("Client", link=get_link())
        await start_transport(self._cfg, self._host_mode)
        await self._dev.power_on()
        await self._dev.connect(self.address)

        self.services: BleakGATTServiceCollection = await self.get_services()
        return True

    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Boolean representing connection status.

        """
        if not self._dev:
            return False
        if not self._connection:
            return False

        await self._dev.disconnect(
            self._connection, HCI_REMOTE_USER_TERMINATED_CONNECTION_ERROR
        )
        return True

    async def pair(self, *args, **kwargs) -> bool:
        """Pair with the peripheral."""
        if not self._peer:
            return False
        await self._peer.connection.pair()
        return True

    async def unpair(self) -> bool:
        """Unpair with the peripheral."""
        warnings.warn(
            "Unpairing is seemingly unavailable in the Bumble API at the moment."
        )
        return False

    @property
    def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        return bool(self._connection)

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if not self._connection:
            raise BleakError("Not connected")

        if self.services is not None:
            return self.services

        new_services = BleakGATTServiceCollection()
        self._peer = Peer(self._connection)
        await self._peer.discover_services()
        for service in self._peer.services:
            new_services.add_service(BleakGATTServiceBumble(service))
            await service.discover_characteristics()
            for characteristic in service.characteristics:
                await characteristic.discover_descriptors()
                new_services.add_characteristic(
                    BleakGATTCharacteristicBumble(
                        characteristic, lambda: self.mtu_size - 3, service
                    )
                )
                for descr in characteristic.descriptors:
                    new_services.add_descriptor(
                        BleakGATTDescriptorBumble(descr, characteristic)
                    )

        return new_services

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        **kwargs,
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to read from,
                specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristic object representing it.

        Returns:
            (bytearray) The read data.

        """
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
            if not characteristic:
                raise BleakCharacteristicNotFoundError(char_specifier)
        else:
            characteristic = char_specifier
        if not self._peer:
            raise BleakError("Not connected")

        char_vals = await self._peer.read_characteristics_by_uuid(
            characteristic.obj.uuid
        )
        value = char_vals[0]
        logger.debug(f"Read Characteristic {characteristic.uuid} : {value.hex()}")
        return bytearray(value)

    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.

        Returns:
            (bytearray) The read data.

        """
        descriptor = self.services.get_descriptor(handle)
        if descriptor is None:
            raise BleakError(f"Descriptor {handle} was not found!")
        val = await descriptor.obj.read_value()
        logger.debug(f"Read Descriptor {handle} : {val}")
        return val

    async def write_gatt_char(
        self,
        characteristic: BleakGATTCharacteristic,
        data: Buffer,
        response: bool,
    ) -> None:
        """
        Perform a write operation on the specified GATT characteristic.

        Args:
            characteristic: The characteristic to write to.
            data: The data to send.
            response: If write-with-response operation should be done.
        """
        await characteristic.obj.write_value(data, with_response=response)
        logger.debug(f"Write Characteristic {characteristic.uuid} : {data}")

    async def write_gatt_descriptor(self, handle: int, data: Buffer) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle: The handle of the descriptor to read from.
            data: The data to send (any bytes-like object).

        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError(f"Descriptor {handle} was not found!")
        await descriptor.obj.write_value(data)
        logger.debug(f"Write Descriptor {handle} : {data}")

    def __notify_handler(self, characteristic: BleakGATTCharacteristic, value):
        for sub in self._subs[characteristic.handle]:
            sub(value)

    async def start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: NotifyCallback,
        **kwargs,
    ) -> None:
        """
        Activate notifications/indications on a characteristic.

        Implementers should call the OS function to enable notifications or
        indications on the characteristic.

        To keep things the same cross-platform, notifications should be preferred
        over indications if possible when a characteristic supports both.
        """
        if not self._subs.get(characteristic.handle):
            self._subs[characteristic.handle] = []
        self._subs[characteristic.handle].append(callback)
        await characteristic.obj.subscribe(
            partial(self.__notify_handler, characteristic)
        )

    async def stop_notify(
        self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID]
    ) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to deactivate
                notification/indication on, specified by either integer handle, UUID or
                directly by the BleakGATTCharacteristic object representing it.

        """
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
            if not characteristic:
                raise BleakCharacteristicNotFoundError(char_specifier)
        else:
            characteristic = char_specifier

        await characteristic.obj.unsubscribe()
        self._subs.pop(characteristic.handle, None)

    def on_connection(self, connection: Connection):
        self._connection = connection
        self._connection.on("disconnection", self.on_disconnection)
        self._subs = {}

    def on_disconnection(self, reason):
        self._connection = None
        self._subs = {}
