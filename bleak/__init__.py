# -*- coding: utf-8 -*-

"""Top-level package for bleak."""

from __future__ import annotations

__author__ = """Henrik Blidh"""
__email__ = "henrik.blidh@gmail.com"

import asyncio
import logging
import os
import sys
import uuid
from typing import TYPE_CHECKING, Callable, List, Optional, Union
from warnings import warn

import async_timeout

if sys.version_info[:2] < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal

from .__version__ import __version__  # noqa: F401
from .backends.characteristic import BleakGATTCharacteristic
from .backends.client import get_platform_client_backend_type
from .backends.device import BLEDevice
from .backends.scanner import (
    AdvertisementData,
    AdvertisementDataCallback,
    AdvertisementDataFilter,
    get_platform_scanner_backend_type,
)
from .backends.service import BleakGATTServiceCollection

if TYPE_CHECKING:
    from .backends.bluezdbus.scanner import BlueZScannerArgs
    from .backends.winrt.client import WinRTClientArgs


_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
if bool(os.environ.get("BLEAK_LOGGING", False)):
    FORMAT = "%(asctime)-15s %(name)-8s %(levelname)s: %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt=FORMAT))
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)


class BleakScanner:
    """
    Interface for Bleak Bluetooth LE Scanners.

    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received. Required on
            macOS >= 12.0, < 12.3 (unless you create an app with ``py2app``).
        scanning_mode:
            Set to ``"passive"`` to avoid the ``"active"`` scanning mode.
            Passive scanning is not supported on macOS! Will raise
            :class:`BleakError` if set to ``"passive"`` on macOS.
        bluez:
            Dictionary of arguments specific to the BlueZ backend.
        **kwargs:
            Additional args for backwards compatibility.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[List[str]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        *,
        bluez: BlueZScannerArgs = {},
        **kwargs,
    ):
        PlatformBleakScanner = get_platform_scanner_backend_type()
        self._backend = PlatformBleakScanner(
            detection_callback, service_uuids, scanning_mode, bluez=bluez, **kwargs
        )

    async def __aenter__(self):
        await self._backend.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._backend.stop()

    def register_detection_callback(
        self, callback: Optional[AdvertisementDataCallback]
    ) -> None:
        """
        Register a callback that is called when a device is discovered or has a property changed.

        .. deprecated:: 0.17.0
            This method will be removed in a future version of Bleak. Pass
            the callback directly to the :class:`BleakScanner` constructor instead.

        Args:
            callback: A function, coroutine or ``None``.


        """
        warn(
            "This method will be removed in a future version of Bleak. Use the detection_callback of the BleakScanner constructor instead.",
            FutureWarning,
            stacklevel=2,
        )
        self._backend.register_detection_callback(callback)

    async def start(self):
        """Start scanning for devices"""
        await self._backend.start()

    async def stop(self):
        """Stop scanning for devices"""
        await self._backend.stop()

    def set_scanning_filter(self, **kwargs):
        """
        Set scanning filter for the BleakScanner.

        .. deprecated:: 0.17.0
            This method will be removed in a future version of Bleak. Pass
            arguments directly to the :class:`BleakScanner` constructor instead.

        Args:
            **kwargs: The filter details.

        """
        warn(
            "This method will be removed in a future version of Bleak. Use BleakScanner constructor args instead.",
            FutureWarning,
            stacklevel=2,
        )
        self._backend.set_scanning_filter(**kwargs)

    @classmethod
    async def discover(cls, timeout=5.0, **kwargs) -> List[BLEDevice]:
        """
        Scan continuously for ``timeout`` seconds and return discovered devices.

        Args:
            timeout:
                Time, in seconds, to scan for.
            **kwargs:
                Additional arguments will be passed to the :class:`BleakScanner`
                constructor.

        Returns:

        """
        async with cls(**kwargs) as scanner:
            await asyncio.sleep(timeout)
            devices = scanner.discovered_devices
        return devices

    @property
    def discovered_devices(self) -> List[BLEDevice]:
        """Gets the devices registered by the BleakScanner.

        Returns:
            A list of the devices that the scanner has discovered during the scanning.
        """
        return self._backend.discovered_devices

    async def get_discovered_devices(self) -> List[BLEDevice]:
        """Gets the devices registered by the BleakScanner.

        .. deprecated:: 0.11.0
            This method will be removed in a future version of Bleak. Use the
            :attr:`.discovered_devices` property instead.

        Returns:
            A list of the devices that the scanner has discovered during the scanning.

        """
        warn(
            "This method will be removed in a future version of Bleak. Use the `discovered_devices` property instead.",
            FutureWarning,
            stacklevel=2,
        )
        return self.discovered_devices

    @classmethod
    async def find_device_by_address(
        cls, device_identifier: str, timeout: float = 10.0, **kwargs
    ) -> Optional[BLEDevice]:
        """A convenience method for obtaining a ``BLEDevice`` object specified by Bluetooth address or (macOS) UUID address.

        Args:
            device_identifier (str): The Bluetooth/UUID address of the Bluetooth peripheral sought.
            timeout (float): Optional timeout to wait for detection of specified peripheral before giving up. Defaults to 10.0 seconds.

        Keyword Args:
            adapter (str): Bluetooth adapter to use for discovery.

        Returns:
            The ``BLEDevice`` sought or ``None`` if not detected.

        """
        device_identifier = device_identifier.lower()
        return await cls.find_device_by_filter(
            lambda d, ad: d.address.lower() == device_identifier,
            timeout=timeout,
            **kwargs,
        )

    @classmethod
    async def find_device_by_filter(
        cls, filter_func: AdvertisementDataFilter, timeout: float = 10.0, **kwargs
    ) -> Optional[BLEDevice]:
        """
        A convenience method for obtaining a ``BLEDevice`` object specified by
        a filter function.

        Args:
            filter_func:
                A function that is called for every BLEDevice found. It should
                return ``True`` only for the wanted device.
            timeout:
                Optional timeout to wait for detection of specified peripheral
                before giving up. Defaults to 10.0 seconds.
            **kwargs:
                Additional arguments to be passed to the :class:`BleakScanner`
                constructor.

        Returns:
            The :class:`BLEDevice` sought or ``None`` if not detected before
            the timeout.

        """
        found_device_queue: asyncio.Queue[BLEDevice] = asyncio.Queue()

        def apply_filter(d: BLEDevice, ad: AdvertisementData):
            if filter_func(d, ad):
                found_device_queue.put_nowait(d)

        async with cls(detection_callback=apply_filter, **kwargs):
            try:
                async with async_timeout.timeout(timeout):
                    return await found_device_queue.get()
            except asyncio.TimeoutError:
                return None


class BleakClient:
    """The Client Interface for Bleak Backend implementations to implement.

    Args:
        device_or_address:
            A :class:`BLEDevice` received from a :class:`BleakScanner` or a
            Bluetooth address (device UUID on macOS).
        disconnected_callback:
            Callback that will be scheduled in the event loop when the client is
            disconnected. The callable must take one argument, which will be
            this client object.
        timeout:
            Timeout in seconds passed to the implicit ``discover`` call when
            ``device_or_address`` is not a :class:`BLEDevice`. Defaults to 10.0.
        winrt:
            Dictionary of WinRT/Windows platform-specific options.
        **kwargs:
            Additional keyword arguments for backwards compatibility.

    .. warning:: Although example code frequently initializes :class:`BleakClient`
        with a Bluetooth address for simplicity, it is not recommended to do so
        for more complex use cases. There are several known issues with providing
        a Bluetooth address as the ``device_or_address`` argument.

        1.  macOS does not provide access to the Bluetooth address for privacy/
            security reasons. Instead it creates a UUID for each Bluetooth
            device which is used in place of the address on this platform.
        2.  Providing an address or UUID instead of a :class:`BLEDevice` causes
            the :meth:`connect` method to implicitly call :meth:`BleakScanner.discover`.
            This is known to cause problems when trying to connect to multiple
            devices at the same time.
    """

    def __init__(
        self,
        device_or_address: Union[BLEDevice, str],
        disconnected_callback: Optional[Callable[[BleakClient], None]] = None,
        *,
        timeout: float = 10.0,
        winrt: WinRTClientArgs = {},
        **kwargs,
    ):
        PlatformBleakClient = get_platform_client_backend_type()
        self._backend = PlatformBleakClient(
            device_or_address,
            disconnected_callback=disconnected_callback,
            timeout=timeout,
            winrt=winrt,
            **kwargs,
        )

    # device info

    @property
    def address(self) -> str:
        """
        Gets the Bluetooth address of this device (UUID on macOS).
        """
        return self._backend.address

    def __str__(self):
        return f"{self.__class__.__name__}, {self.address}"

    def __repr__(self):
        return f"<{self.__class__.__name__}, {self.address}, {type(self._backend)}>"

    # Async Context managers

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    # Connectivity methods

    def set_disconnected_callback(
        self, callback: Optional[Callable[[BleakClient], None]], **kwargs
    ) -> None:
        """Set the disconnect callback.

        .. deprecated:: 0.17.0
            This method will be removed in a future version of Bleak.
            Pass the callback to the :class:`BleakClient` constructor instead.

        Args:
            callback: callback to be called on disconnection.

        """
        warn(
            "This method will be removed future version, pass the callback to the BleakClient constructor instead.",
            FutureWarning,
            stacklevel=2,
        )
        self._backend.set_disconnected_callback(callback, **kwargs)

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Args:
            **kwargs: For backwards compatibility - should not be used.

        Returns:
            Always returns ``True`` for backwards compatibility.

        """
        return await self._backend.connect(**kwargs)

    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Always returns ``True`` for backwards compatibility.

        """
        return await self._backend.disconnect()

    async def pair(self, *args, **kwargs) -> bool:
        """
        Pair with the peripheral.

        Returns:
            Always returns ``True`` for backwards compatibility.

        """
        return await self._backend.pair(*args, **kwargs)

    async def unpair(self) -> bool:
        """
        Unpair with the peripheral.

        Returns:
            Always returns ``True`` for backwards compatibility.
        """
        return await self._backend.unpair()

    @property
    def is_connected(self) -> bool:
        """
        Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        return self._backend.is_connected

    # GATT services methods

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        .. deprecated:: 0.17.0
            This method will be removed in a future version of Bleak.
            Use the :attr:`services` property instead.

        Returns:
           A :class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        warn(
            "This method will be removed future version, use the services property instead.",
            FutureWarning,
            stacklevel=2,
        )
        return await self._backend.get_services(**kwargs)

    @property
    def services(self) -> BleakGATTServiceCollection:
        """
        Gets the collection of GATT services available on the device.

        The returned value is only valid as long as the device is connected.
        """
        return self._backend.services

    # I/O methods

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        **kwargs,
    ) -> bytearray:
        """
        Perform read operation on the specified GATT characteristic.

        Args:
            char_specifier:
                The characteristic to read from, specified by either integer
                handle, UUID or directly by the BleakGATTCharacteristic object
                representing it.

        Returns:
            The read data.

        """
        return await self._backend.read_gatt_char(char_specifier, **kwargs)

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: Union[bytes, bytearray, memoryview],
        response: bool = False,
    ) -> None:
        """
        Perform a write operation on the specified GATT characteristic.

        Args:
            char_specifier:
                The characteristic to write to, specified by either integer
                handle, UUID or directly by the BleakGATTCharacteristic object
                representing it.
            data:
                The data to send.
            response:
                If write-with-response operation should be done. Defaults to ``False``.

        """
        await self._backend.write_gatt_char(char_specifier, data, response)

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs,
    ) -> None:
        """
        Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be a integer handle of
        the characteristic generating the data and the second will be a ``bytearray``.

        .. code-block:: python

            def callback(sender: int, data: bytearray):
                print(f"{sender}: {data}")
            client.start_notify(char_uuid, callback)

        Args:
            char_specifier:
                The characteristic to activate notifications/indications on a
                characteristic, specified by either integer handle,
                UUID or directly by the BleakGATTCharacteristic object representing it.
            callback:
                The function to be called on notification.

        """
        await self._backend.start_notify(char_specifier, callback, **kwargs)

    async def stop_notify(
        self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID]
    ) -> None:
        """
        Deactivate notification/indication on a specified characteristic.

        Args:
            char_specifier:
                The characteristic to deactivate notification/indication on,
                specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristic object representing it.

        .. tip:: Notifications are stopped automatically on disconnect, so this
            method does not need to be called unless notifications need to be
            stopped some time before the device disconnects.
        """
        await self._backend.stop_notify(char_specifier)

    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        """
        Perform read operation on the specified GATT descriptor.

        Args:
            handle: The handle of the descriptor to read from.

        Returns:
            The read data.

        """
        return await self._backend.read_gatt_descriptor(handle, **kwargs)

    async def write_gatt_descriptor(
        self, handle: int, data: Union[bytes, bytearray, memoryview]
    ) -> None:
        """
        Perform a write operation on the specified GATT descriptor.

        Args:
            handle:
                The handle of the descriptor to read from.
            data:
                The data to send.

        """
        await self._backend.write_gatt_descriptor(handle, data)


# for backward compatibility
def discover():
    """
    .. deprecated:: 0.17.0
        This method will be removed in a future version of Bleak.
        Use :meth:`BleakScanner.discover` instead.
    """
    warn(
        "The discover function will removed in a future version, use BleakScanner.discover instead.",
        FutureWarning,
        stacklevel=2,
    )
    return BleakScanner.discover()


def cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Perform Bluetooth Low Energy device scan"
    )
    parser.add_argument("-i", dest="adapter", default=None, help="HCI device")
    parser.add_argument(
        "-t", dest="timeout", type=int, default=5, help="Duration to scan for"
    )
    args = parser.parse_args()

    out = asyncio.run(discover(adapter=args.adapter, timeout=float(args.timeout)))
    for o in out:
        print(str(o))


if __name__ == "__main__":
    cli()
