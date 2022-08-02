# -*- coding: utf-8 -*-
"""
Base class for backend clients.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
import asyncio
import uuid
from typing import Callable, Optional, Union
from warnings import warn

from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak import abstract_api


class BaseBleakClient(abstract_api.AbstractBleakClient):
    """The Client Interface for Bleak Backend implementations to implement.

    The documentation of this interface should thus be safe to use as a reference for your implementation.

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
        timeout (float): Timeout for required ``discover`` call. Defaults to 10.0.
        disconnected_callback (callable): Callback that will be scheduled in the
            event loop when the client is disconnected. The callable must take one
            argument, which will be this client object.
    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        if isinstance(address_or_ble_device, BLEDevice):
            self.address = address_or_ble_device.address
        else:
            self.address = address_or_ble_device

        self.services = BleakGATTServiceCollection()

        self._services_resolved = False
        self._notification_callbacks = {}

        self._timeout = kwargs.get("timeout", 10.0)
        self._disconnected_callback = kwargs.get("disconnected_callback")

    def __str__(self):
        return "{0}, {1}".format(self.__class__.__name__, self.address)

    def __repr__(self):
        return "<{0}, {1}, {2}>".format(
            self.__class__.__name__,
            self.address,
            super(BaseBleakClient, self).__repr__(),
        )

    class _DeprecatedIsConnectedReturn:
        """Wrapper for ``is_connected`` return value to provide deprecation warning."""

        def __init__(self, value: bool):
            self._value = value

        def __bool__(self):
            return self._value

        def __call__(self) -> bool:
            warn(
                "is_connected has been changed to a property. Calling it as an async method will be removed in a future version",
                FutureWarning,
                stacklevel=2,
            )
            f = asyncio.Future()
            f.set_result(self._value)
            return f

        def __repr__(self) -> str:
            return repr(self._value)

    # GATT services methods
