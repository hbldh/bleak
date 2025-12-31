# Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>
"""
Base class for backend clients.
"""
import abc
from collections.abc import Callable
from typing import Any, Optional, Union

from bleak.args import SizedBuffer
from bleak.backends import BleakBackend, get_default_backend
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakError

NotifyCallback = Callable[[bytearray], None]


class BaseBleakClient(abc.ABC):
    """The Client Interface for Bleak Backend implementations to implement.

    The documentation of this interface should thus be safe to use as a reference for your implementation.

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
        timeout (float): Timeout for required ``discover`` call.
        disconnected_callback (callable): Callback that will be scheduled in the
            event loop when the client is disconnected. The callable must take one
            argument, which will be this client object.
    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs: Any):
        if isinstance(address_or_ble_device, BLEDevice):
            self.address = address_or_ble_device.address
        else:
            self.address = address_or_ble_device

        self.services: Optional[BleakGATTServiceCollection] = None

        self._timeout = kwargs["timeout"]
        self._disconnected_callback: Optional[Callable[[], None]] = kwargs.get(
            "disconnected_callback"
        )

    # NB: this is not marked as @abc.abstractmethod because that would break
    # 3rd-party backends. We might change this in the future to make it required.
    @property
    def name(self) -> str:
        """See :meth:`bleak.BleakClient.name`."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def mtu_size(self) -> int:
        """Gets the negotiated MTU."""
        raise NotImplementedError

    # Connectivity methods

    def set_disconnected_callback(
        self, callback: Optional[Callable[[], None]], **kwargs: Any
    ) -> None:
        """Set the disconnect callback.
        The callback will only be called on unsolicited disconnect event.

        Set the callback to ``None`` to remove any existing callback.

        Args:
            callback: callback to be called on disconnection.

        """
        self._disconnected_callback = callback

    @abc.abstractmethod
    async def connect(self, pair: bool, **kwargs: Any) -> None:
        """Connect to the specified GATT server.

        Args:
            pair (bool): If the client should attempt to pair with the
            peripheral before connecting if it is not already paired.

            Backends that can't implement this should make an appropriate
            log message and ignore the parameter.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the specified GATT server."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def pair(self, *args: Any, **kwargs: Any) -> None:
        """Pair with the peripheral."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def unpair(self) -> None:
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

    # I/O methods

    @abc.abstractmethod
    async def read_gatt_char(
        self, characteristic: BleakGATTCharacteristic, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to read from.

        Returns:
            (bytearray) The read data.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def read_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            descriptor: The descriptor to read from.

        Returns:
            The read data.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_char(
        self, characteristic: BleakGATTCharacteristic, data: SizedBuffer, response: bool
    ) -> None:
        """
        Perform a write operation on the specified GATT characteristic.

        Args:
            characteristic: The characteristic to write to.
            data: The data to send.
            response: If write-with-response operation should be done.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, data: SizedBuffer
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            descriptor: The descriptor to read from.
            data: The data to send (any bytes-like object).

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: NotifyCallback,
        **kwargs: Any,
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
    async def stop_notify(self, characteristic: BleakGATTCharacteristic) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to deactivate
                notification/indication on.

        """
        raise NotImplementedError()


def get_platform_client_backend_type() -> tuple[type[BaseBleakClient], BleakBackend]:
    """
    Gets the platform-specific :class:`BaseBleakClient` type.
    """
    backend = get_default_backend()
    match backend:
        case BleakBackend.P4ANDROID:
            from bleak.backends.p4android.client import (
                BleakClientP4Android,  # type: ignore
            )

            return (BleakClientP4Android, backend)  # type: ignore

        case BleakBackend.BLUEZ_DBUS:
            from bleak.backends.bluezdbus.client import (
                BleakClientBlueZDBus,  # type: ignore
            )

            return (BleakClientBlueZDBus, backend)  # type: ignore

        case BleakBackend.PYTHONISTA_CB:
            try:
                from bleak_pythonista import BleakClientPythonistaCB  # type: ignore

                return (BleakClientPythonistaCB, backend)  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "Ensure you have `bleak-pythonista` package installed."
                ) from e

        case BleakBackend.CORE_BLUETOOTH:
            from bleak.backends.corebluetooth.client import (
                BleakClientCoreBluetooth,  # type: ignore
            )

            return (BleakClientCoreBluetooth, backend)  # type: ignore

        case BleakBackend.WIN_RT:
            from bleak.backends.winrt.client import BleakClientWinRT  # type: ignore

            return (BleakClientWinRT, backend)  # type: ignore

        case _:
            raise BleakError(f"Unsupported backend: {backend}")
