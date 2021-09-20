# -*- coding: utf-8 -*-
"""
Base class for backend clients.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
import asyncio
import uuid
from typing import Callable, Union, Optional
from warnings import warn

from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice


PairingCallback = Callable[
    [str, Union[None, str], Union[None, int]], Union[bool, int, str, None]
]
"""Type of the pairing callback function

Args:
    device (str): Address of the peer device participating in the pairing process.
    pin (None or str): If this parameter is not `None`, then this callback is invoked
        because the service daemon needs to display a pincode for an authentication.
        The application must display the given PIN to the user, who will then need to
        either enter this PIN on the peer device that is being paired (if such device
        has input but no output capabilities), or confirm that the PIN matches the one
        shown on the peer device.
        Return `True` to proceed with the pairing or `False` to reject/cancel it. Note,
        however, that canceling the pairing at this point might still result in device
        being paired, because for some pairing methods, the system and the target
        device don't need any confirmation.
    passkey (None or int): Very similar to `pin` argument, just that this value is used
        on some systems when Passkey Entry pairing method is initiated. On some systems
        this will always be `None` and passkey is provided as `pin` argument.
        If not `None`, the passkey will always represent a 6-digit number, so the
        display should be zero-padded at the start if the value contains less than 6
        digits.
        Return value logic is the same as for `pin` - return `True` to proceed with the
        pairing or `False` to reject/cancel it.

Returns:
    `True` to confirm pairing with provided `pin` or `passkey`, if any of them is not `None`.
    If `pin` and `passkey` are both `None`, it means that this callback got invoked because
    the service daemon needs to get the pincode or passkey for an authentication. The return
    value should be an alphanumeric string of 1-16 characters length (pincode) or a numeric
    value between 0-999999 (passkey).
    Pairing is rejected if `None` is returned.
"""


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

    # Async Context managers

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

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
    async def pair(
        self, *args, callback: Optional[PairingCallback] = None, **kwargs
    ) -> bool:
        """Pair with the peripheral.

        Args:
            callback (`PairingCallback`): callback to be called to provide or confirm pairing pin
                or passkey. If not provided and Bleak is registered as a pairing agent/manager
                instead of system pairing manager, then all display- and confirm-based pairing
                requests will be accepted, and requests requiring pin or passkey input will be
                canceled.

        Returns:
            Boolean representing success of pairing.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def unpair(self) -> bool:
        """Unpair with the peripheral."""
        raise NotImplementedError()

    @abc.abstractproperty
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
                "is_connected has been changed to a property. Calling it as an async method will be removed in a "
                "future version",
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
        **kwargs
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
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs
    ) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be a integer handle of the characteristic generating the
        data and the second will be a ``bytearray``.

        .. code-block:: python

            def callback(sender: int, data: bytearray):
                print(f"{sender}: {data}")
            client.start_notify(char_uuid, callback)

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to activate
                notifications/indications on a characteristic, specified by either integer handle,
                UUID or directly by the BleakGATTCharacteristic object representing it.
            callback (function): The function to be called on notification.

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
