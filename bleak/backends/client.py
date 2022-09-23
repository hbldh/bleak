# -*- coding: utf-8 -*-
"""
Base class for backend clients.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
import asyncio
import os
import platform
import uuid
from typing import Callable, Optional, Type, Union
from warnings import warn

from ..exc import BleakError
from .service import BleakGATTServiceCollection
from .characteristic import BleakGATTCharacteristic
from .device import BLEDevice

NotifyCallback = Callable[[bytearray], None]


class BaseBleakClient(abc.ABC):
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

        self._timeout = kwargs.get("timeout", 10.0)
        self._disconnected_callback = kwargs.get("disconnected_callback")

    @property
    @abc.abstractmethod
    def mtu_size(self) -> int:
        """Gets the negotiated MTU."""
        raise NotImplementedError

    # Connectivity methods

    def set_disconnected_callback(
        self, callback: Optional[Callable[["BaseBleakClient"], None]], **kwargs
    ) -> None:
        """Set the disconnect callback.
        The callback will only be called on unsolicited disconnect event.

        Callbacks must accept one input which is the client object itself.

        Set the callback to ``None`` to remove any existing callback.

        .. code-block:: python

            def callback(client):
                print("Client with address {} got disconnected!".format(client.address))

            client.set_disconnected_callback(callback)
            client.connect()

        Args:
            callback: callback to be called on disconnection.

        """
        self._disconnected_callback = callback

    @abc.abstractmethod
    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Returns:
            Boolean representing connection status.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Boolean representing connection status.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def pair(self, *args, **kwargs) -> bool:
        """Pair with the peripheral."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def unpair(self) -> bool:
        """Unpair with the peripheral."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        raise NotImplementedError()

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

    @abc.abstractmethod
    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        raise NotImplementedError()

    # I/O methods

    @abc.abstractmethod
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
        raise NotImplementedError()

    @abc.abstractmethod
    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.

        Returns:
            (bytearray) The read data.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: Union[bytes, bytearray, memoryview],
        response: bool = False,
    ) -> None:
        """Perform a write operation on the specified GATT characteristic.

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to write
                to, specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristic object representing it.
            data (bytes or bytearray): The data to send.
            response (bool): If write-with-response operation should be done. Defaults to `False`.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_descriptor(
        self, handle: int, data: Union[bytes, bytearray, memoryview]
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            data (bytes or bytearray): The data to send.

        """
        raise NotImplementedError()

    @abc.abstractmethod
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
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop_notify(
        self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID]
    ) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to deactivate
                notification/indication on, specified by either integer handle, UUID or
                directly by the BleakGATTCharacteristic object representing it.

        """
        raise NotImplementedError()


def get_platform_client_backend_type() -> Type[BaseBleakClient]:
    """
    Gets the platform-specific :class:`BaseBleakClient` type.
    """
    if os.environ.get("P4A_BOOTSTRAP") is not None:
        from bleak.backends.p4android.client import BleakClientP4Android

        return BleakClientP4Android

    if platform.system() == "Linux":
        from bleak.backends.bluezdbus.client import BleakClientBlueZDBus

        return BleakClientBlueZDBus

    if platform.system() == "Darwin":
        from bleak.backends.corebluetooth.client import BleakClientCoreBluetooth

        return BleakClientCoreBluetooth

    if platform.system() == "Windows":
        from bleak.backends.winrt.client import BleakClientWinRT

        return BleakClientWinRT

    raise BleakError(f"Unsupported platform: {platform.system()}")
