# -*- coding: utf-8 -*-
"""
Base class for backend clients.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
import asyncio
from typing import Callable, Any

from bleak.backends.service import BleakGATTServiceCollection


class BaseBleakClient(abc.ABC):
    """The Client Interface for Bleak Backend implementations to implement."""

    def __init__(self, address, loop=None, **kwargs):
        self.address = address
        self.loop = loop if loop else asyncio.get_event_loop()

        self.services = BleakGATTServiceCollection()

        self._services_resolved = False
        self._notification_callbacks = {}

    def __str__(self):
        return "{0}, {1}".format(self.__class__.__name__, self.address)

    def __repr__(self):
        return "<{0}, {1}, {2}>".format(
            self.__class__.__name__, self.address, self.loop
        )

    # Async Context managers

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    # Connectivity methods

    @abc.abstractmethod
    async def connect(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    async def disconnect(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    async def is_connected(self) -> bool:
        raise NotImplementedError()

    # GATT services methods

    @abc.abstractmethod
    async def get_services(self) -> BleakGATTServiceCollection:
        raise NotImplementedError()

    # I/O methods

    @abc.abstractmethod
    async def read_gatt_char(self, _uuid: str) -> bytearray:
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_char(
        self, _uuid: str, data: bytearray, response: bool = False
    ) -> Any:
        raise NotImplementedError()

    @abc.abstractmethod
    async def read_gatt_descriptor(self, handle: int) -> bytearray:
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_descriptor(
        self, _uuid: str, data: bytearray, response: bool = False
    ) -> Any:
        raise NotImplementedError()

    @abc.abstractmethod
    async def start_notify(
        self, _uuid: str, callback: Callable[[str, Any], Any], **kwargs
    ) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop_notify(self, _uuid: str) -> None:
        raise NotImplementedError()
