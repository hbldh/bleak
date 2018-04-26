# -*- coding: utf-8 -*-
"""
Base class for backend clients.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""
import asyncio
from typing import Callable, Any


class BaseBleakClient(object):
    """The Client Interface for Bleak Backend implementations to implement."""

    def __init__(self, address, loop=None, **kwargs):
        self.address = address
        self.loop = loop if loop else asyncio.get_event_loop()
        self.services = {}
        self.characteristics = {}

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

    async def connect(self) -> bool:
        raise NotImplementedError()

    async def disconnect(self) -> bool:
        raise NotImplementedError()

    async def is_connected(self) -> bool:
        raise NotImplementedError()

    # GATT services methods

    async def get_services(self):
        raise NotImplementedError()

    # I/O methods

    async def read_gatt_char(self, _uuid: str) -> bytearray:
        raise NotImplementedError()

    async def write_gatt_char(
        self,
        _uuid: str,
        data: bytearray,
        response: bool = False
    ) -> Any:
        raise NotImplementedError()

    async def start_notify(
        self,
        _uuid: str,
        callback: Callable[[str, Any], Any],
        **kwargs
    ) -> None:
        raise NotImplementedError()

    async def stop_notify(self, _uuid: str) -> None:
        raise NotImplementedError()
