# -*- coding: utf-8 -*-

"""Top-level package for bleak."""

from __future__ import annotations

__author__ = """Henrik Blidh"""
__email__ = "henrik.blidh@gmail.com"

import asyncio
import functools
import inspect
import logging
import os
import sys
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable
from types import TracebackType
from typing import Any, Literal, Optional, TypedDict, Union, cast, overload

if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer

if sys.version_info < (3, 11):
    from async_timeout import timeout as async_timeout
    from typing_extensions import Never, Self, Unpack, assert_never
else:
    from asyncio import timeout as async_timeout
    from typing import Never, Self, Unpack, assert_never

from bleak.args.bluez import BlueZScannerArgs
from bleak.args.corebluetooth import CBScannerArgs, CBStartNotifyArgs
from bleak.args.winrt import WinRTClientArgs
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient, get_platform_client_backend_type
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import (
    AdvertisementData,
    AdvertisementDataCallback,
    AdvertisementDataFilter,
    BaseBleakScanner,
    get_platform_scanner_backend_type,
)
from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakCharacteristicNotFoundError, BleakError
from bleak.uuids import normalize_uuid_str

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
if bool(os.environ.get("BLEAK_LOGGING", False)):
    FORMAT = "%(asctime)-15s %(name)-8s %(threadName)s %(levelname)s: %(message)s"
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt=FORMAT))
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)


# prevent tasks from being garbage collected
_background_tasks = set[asyncio.Task[None]]()


class BleakScanner:
    """
    Interface for Bleak Bluetooth LE Scanners.

    The scanner will listen for BLE advertisements, optionally filtering on advertised services or
    other conditions, and collect a list of :class:`BLEDevice` objects. These can subsequently be used to
    connect to the corresponding BLE server.

    A :class:`BleakScanner` can be used as an asynchronous context manager in which case it automatically
    starts and stops scanning.

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
        cb:
            Dictionary of arguments specific to the CoreBluetooth backend.
        backend:
            Used to override the automatically selected backend (i.e. for a
            custom backend).
        **kwargs:
            Additional args for backwards compatibility.

    .. tip:: The first received advertisement in ``detection_callback`` may or
        may not include scan response data if the remote device supports it.
        Be sure to take this into account when handing the callback. For example,
        the scan response often contains the local name of the device so if you
        are matching a device based on other data but want to display the local
        name to the user, be sure to wait for ``adv_data.local_name is not None``.

    .. versionchanged:: 0.15
        ``detection_callback``, ``service_uuids`` and ``scanning_mode`` are no longer keyword-only.
        Added ``bluez`` parameter.

    .. versionchanged:: 0.18
        No longer is alias for backend type and no longer inherits from :class:`BaseBleakScanner`.
        Added ``backend`` parameter.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[list[str]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        *,
        bluez: BlueZScannerArgs = {},
        cb: CBScannerArgs = {},
        backend: Optional[type[BaseBleakScanner]] = None,
        **kwargs: Any,
    ) -> None:
        PlatformBleakScanner = (
            get_platform_scanner_backend_type() if backend is None else backend
        )

        self._backend = PlatformBleakScanner(
            detection_callback,
            service_uuids,
            scanning_mode,  # type: ignore
            bluez=bluez,
            cb=cb,
            **kwargs,
        )  # type: ignore

    async def __aenter__(self) -> Self:
        await self._backend.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        await self._backend.stop()

    async def start(self) -> None:
        """Start scanning for devices"""
        await self._backend.start()

    async def stop(self) -> None:
        """Stop scanning for devices"""
        await self._backend.stop()

    async def advertisement_data(
        self,
    ) -> AsyncGenerator[tuple[BLEDevice, AdvertisementData], None]:
        """
        Yields devices and associated advertising data packets as they are discovered.

        .. note::
            Ensure that scanning is started before calling this method.

        Returns:
            An async iterator that yields tuples (:class:`BLEDevice`, :class:`AdvertisementData`).

        .. versionadded:: 0.21
        """
        devices = asyncio.Queue[tuple[BLEDevice, AdvertisementData]]()

        unregister_callback = self._backend.register_detection_callback(
            lambda bd, ad: devices.put_nowait((bd, ad))
        )
        try:
            while True:
                yield await devices.get()
        finally:
            unregister_callback()

    class ExtraArgs(TypedDict, total=False):
        """
        Keyword args from :class:`~bleak.BleakScanner` that can be passed to
        other convenience methods.
        """

        service_uuids: list[str]
        """
        Optional list of service UUIDs to filter on. Only advertisements
        containing this advertising data will be received. Required on
        macOS >= 12.0, < 12.3 (unless you create an app with ``py2app``).
        """
        scanning_mode: Literal["active", "passive"]
        """
        Set to ``"passive"`` to avoid the ``"active"`` scanning mode.
        Passive scanning is not supported on macOS! Will raise
        :class:`BleakError` if set to ``"passive"`` on macOS.
        """
        bluez: BlueZScannerArgs
        """
        Dictionary of arguments specific to the BlueZ backend.
        """
        cb: CBScannerArgs
        """
        Dictionary of arguments specific to the CoreBluetooth backend.
        """
        backend: type[BaseBleakScanner]
        """
        Used to override the automatically selected backend (i.e. for a
            custom backend).
        """

    @overload
    @classmethod
    async def discover(
        cls,
        timeout: float = 5.0,
        *,
        return_adv: Literal[False] = False,
        **kwargs: Unpack[ExtraArgs],
    ) -> list[BLEDevice]: ...

    @overload
    @classmethod
    async def discover(
        cls,
        timeout: float = 5.0,
        *,
        return_adv: Literal[True],
        **kwargs: Unpack[ExtraArgs],
    ) -> dict[str, tuple[BLEDevice, AdvertisementData]]: ...

    @classmethod
    async def discover(
        cls,
        timeout: float = 5.0,
        *,
        return_adv: bool = False,
        **kwargs: Unpack[ExtraArgs],
    ):
        """
        Scan continuously for ``timeout`` seconds and return discovered devices.

        Args:
            timeout:
                Time, in seconds, to scan for.
            return_adv:
                If ``True``, the return value will include advertising data.
            **kwargs:
                Additional arguments will be passed to the :class:`BleakScanner`
                constructor.

        Returns:
            The value of :attr:`discovered_devices_and_advertisement_data` if
            ``return_adv`` is ``True``, otherwise the value of :attr:`discovered_devices`.

        .. versionchanged:: 0.19
            Added ``return_adv`` parameter.
        """
        async with cls(**kwargs) as scanner:
            await asyncio.sleep(timeout)

        if return_adv:
            return scanner.discovered_devices_and_advertisement_data

        return scanner.discovered_devices

    @property
    def discovered_devices(self) -> list[BLEDevice]:
        """
        Gets list of the devices that the scanner has discovered during the scanning.

        If you also need advertisement data, use :attr:`discovered_devices_and_advertisement_data` instead.
        """
        return [d for d, _ in self._backend.seen_devices.values()]

    @property
    def discovered_devices_and_advertisement_data(
        self,
    ) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        """
        Gets a map of device address to tuples of devices and the most recently
        received advertisement data for that device.

        The address keys are useful to compare the discovered devices to a set
        of known devices. If you don't need to do that, consider using
        ``discovered_devices_and_advertisement_data.values()`` to just get the
        values instead.

        .. versionadded:: 0.19
        """
        return {d[0].address: d for d in self._backend.seen_devices.values()}

    @classmethod
    async def find_device_by_address(
        cls, device_identifier: str, timeout: float = 10.0, **kwargs: Unpack[ExtraArgs]
    ) -> Optional[BLEDevice]:
        """Obtain a ``BLEDevice`` for a BLE server specified by Bluetooth address or (macOS) UUID address.

        Args:
            device_identifier: The Bluetooth/UUID address of the Bluetooth peripheral sought.
            timeout: Optional timeout to wait for detection of specified peripheral before giving up. Defaults to 10.0 seconds.
            **kwargs: additional args passed to the :class:`BleakScanner` constructor.

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
    async def find_device_by_name(
        cls, name: str, timeout: float = 10.0, **kwargs: Unpack[ExtraArgs]
    ) -> Optional[BLEDevice]:
        """Obtain a ``BLEDevice`` for a BLE server specified by the local name in the advertising data.

        Args:
            name: The name sought.
            timeout: Optional timeout to wait for detection of specified peripheral before giving up. Defaults to 10.0 seconds.
            **kwargs: additional args passed to the :class:`BleakScanner` constructor.

        Returns:
            The ``BLEDevice`` sought or ``None`` if not detected.

        .. versionadded:: 0.20
        """
        return await cls.find_device_by_filter(
            lambda d, ad: ad.local_name == name,
            timeout=timeout,
            **kwargs,
        )

    @classmethod
    async def find_device_by_filter(
        cls,
        filterfunc: AdvertisementDataFilter,
        timeout: float = 10.0,
        **kwargs: Unpack[ExtraArgs],
    ) -> Optional[BLEDevice]:
        """Obtain a ``BLEDevice`` for a BLE server that matches a given filter function.

        This can be used to find a BLE server by other identifying information than its address,
        for example its name.

        Args:
            filterfunc:
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
        async with cls(**kwargs) as scanner:
            try:
                async with async_timeout(timeout):
                    async for bd, ad in scanner.advertisement_data():
                        if filterfunc(bd, ad):
                            return bd
                    assert_never(cast(Never, "advertisement_data() should never stop"))
            except asyncio.TimeoutError:
                return None


def _resolve_characteristic(
    char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
    services: BleakGATTServiceCollection,
) -> BleakGATTCharacteristic:

    if isinstance(char_specifier, BleakGATTCharacteristic):
        return char_specifier

    characteristic = services.get_characteristic(char_specifier)

    if not characteristic:
        raise BleakCharacteristicNotFoundError(char_specifier)

    return characteristic


def _resolve_descriptor(
    desc_specifier: Union[BleakGATTDescriptor, int],
    services: BleakGATTServiceCollection,
) -> BleakGATTDescriptor:

    if isinstance(desc_specifier, BleakGATTDescriptor):
        return desc_specifier

    characteristic = services.get_descriptor(desc_specifier)

    if not characteristic:
        raise BleakError(f"Descriptor with handle {desc_specifier} was not found!")

    return characteristic


class BleakClient:
    """The Client interface for connecting to a specific BLE GATT server and communicating with it.

    A BleakClient can be used as an asynchronous context manager in which case it automatically
    connects and disconnects.

    How many BLE connections can be active simultaneously, and whether connections can be active while
    scanning depends on the Bluetooth adapter hardware.

    Args:
        address_or_ble_device:
            A :class:`BLEDevice` received from a :class:`BleakScanner` or a
            Bluetooth address (device UUID on macOS).
        disconnected_callback:
            Callback that will be scheduled in the event loop when the client is
            disconnected. The callable must take one argument, which will be
            this client object.
        services:
            Optional list of services to filter. If provided, only these services
            will be resolved. This may or may not reduce the time needed to
            enumerate the services depending on if the OS supports such filtering
            in the Bluetooth stack or not (should affect Windows and Mac).
            These can be 16-bit or 128-bit UUIDs.
        timeout:
            Timeout in seconds passed to the implicit ``discover`` call when
            ``address_or_ble_device`` is not a :class:`BLEDevice`. Defaults to 10.0.
        pair:
            Attempt to pair with the the device before connecting, if it is not
            already paired. This has no effect on macOS since pairing is initiated
            automatically when accessing a characteristic that requires authentication.
            In rare cases, on other platforms, it might be necessary to pair the
            device first in order to be able to even enumerate the services during
            the connection process.
        winrt:
            Dictionary of WinRT/Windows platform-specific options.
        backend:
            Used to override the automatically selected backend (i.e. for a
            custom backend).
        **kwargs:
            Additional keyword arguments for backwards compatibility.

    .. tip:: If you enable pairing with the ``pair`` argument, you will also
        want to extend the timeout to allow enough time for the user to find
        and enter the PIN code on the device, if required.

    .. warning:: Although example code frequently initializes :class:`BleakClient`
        with a Bluetooth address for simplicity, it is not recommended to do so
        for more complex use cases. There are several known issues with providing
        a Bluetooth address as the ``address_or_ble_device`` argument.

        1.  macOS does not provide access to the Bluetooth address for privacy/
            security reasons. Instead it creates a UUID for each Bluetooth
            device which is used in place of the address on this platform.
        2.  Providing an address or UUID instead of a :class:`BLEDevice` causes
            the :meth:`connect` method to implicitly call :meth:`BleakScanner.discover`.
            This is known to cause problems when trying to connect to multiple
            devices at the same time.

    .. versionchanged:: 0.15
        ``disconnected_callback`` is no longer keyword-only. Added ``winrt`` parameter.

    .. versionchanged:: 0.18
        No longer is alias for backend type and no longer inherits from :class:`BaseBleakClient`.
        Added ``backend`` parameter.

    .. versionchanged:: 1.0
        Added ``pair`` parameter.
    """

    def __init__(
        self,
        address_or_ble_device: Union[BLEDevice, str],
        disconnected_callback: Optional[Callable[[BleakClient], None]] = None,
        services: Optional[Iterable[str]] = None,
        *,
        timeout: float = 10.0,
        pair: bool = False,
        winrt: WinRTClientArgs = {},
        backend: Optional[type[BaseBleakClient]] = None,
        **kwargs: Any,
    ) -> None:
        PlatformBleakClient = (
            get_platform_client_backend_type() if backend is None else backend
        )

        self._backend = PlatformBleakClient(
            address_or_ble_device,
            disconnected_callback=(
                None
                if disconnected_callback is None
                else functools.partial(disconnected_callback, self)
            ),
            services=(
                None if services is None else set(map(normalize_uuid_str, services))
            ),
            timeout=timeout,
            winrt=winrt,
            **kwargs,
        )
        self._pair_before_connect = pair

    # device info

    @property
    def name(self) -> str:
        """
        Gets a human-readable name for the peripheral device.

        The name can be somewhat OS-dependent. It is usually the name provided
        by the standard Device Name characteristic, if present or the name
        provided by the advertising data. If neither is available, it will be
        a Bluetooth address separated with dashes (``-``) instead of colons
        (``:``) (or a UUID on Apple devices). It may also be possible to override
        the device name using the OS's Bluetooth settings.
        """
        return self._backend.name

    @property
    def address(self) -> str:
        """
        Gets the Bluetooth address of this device (UUID on macOS).
        """
        return self._backend.address

    @property
    def mtu_size(self) -> int:
        """
        Gets the negotiated MTU size in bytes for the active connection.

        Consider using :attr:`bleak.backends.characteristic.BleakGATTCharacteristic.max_write_without_response_size` instead.

        .. warning:: The BlueZ backend will always return 23 (the minimum MTU size).
            See the ``mtu_size.py`` example for a way to hack around this.

        """
        return self._backend.mtu_size

    def __str__(self) -> str:
        return f"{self.__class__.__name__}, {self.address}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}, {self.address}, {type(self._backend)}>"

    # Async Context managers

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.disconnect()

    # Connectivity methods

    async def connect(self, **kwargs: Any) -> None:
        """Connect to the specified GATT server.

        Args:
            **kwargs: For backwards compatibility - should not be used.

        .. versionchanged:: 1.0
            No longer returns ``True``. Instead, the return type is ``None``.
        """
        await self._backend.connect(self._pair_before_connect, **kwargs)

    async def disconnect(self) -> None:
        """Disconnect from the specified GATT server.

        .. versionchanged:: 1.0
            No longer returns ``True``. Instead, the return type is ``None``.
        """
        await self._backend.disconnect()

    async def pair(self, *args: Any, **kwargs: Any) -> None:
        """
        Pair with the specified GATT server.

        This method is not available on macOS. Instead of manually initiating
        paring, the user will be prompted to pair the device the first time
        that a characteristic that requires authentication is read or written.
        This method may have backend-specific additional keyword arguments.

        .. versionchanged:: 1.0
            No longer returns ``True``. Instead, the return type is ``None``.
        """
        await self._backend.pair(*args, **kwargs)

    async def unpair(self) -> None:
        """
        Unpair from the specified GATT server.

        Unpairing will also disconnect the device.

        This method is only available on Windows and Linux and will raise an
        exception on other platforms.

        .. versionchanged:: 1.0
            No longer returns ``True``. Instead, the return type is ``None``.
        """
        await self._backend.unpair()

    @property
    def is_connected(self) -> bool:
        """
        Check connection status between this client and the GATT server.

        Returns:
            Boolean representing connection status.

        """
        return self._backend.is_connected

    # GATT services methods

    @property
    def services(self) -> BleakGATTServiceCollection:
        """
        Gets the collection of GATT services available on the device.

        The returned value is only valid as long as the device is connected.

        Raises:
            BleakError: if service discovery has not been performed yet during this connection.
        """
        if not self._backend.services:
            raise BleakError("Service Discovery has not been performed yet")

        return self._backend.services

    # I/O methods

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        **kwargs: Any,
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

        Raises:
            BleakGattCharacteristicNotFoundError: if a characteristic with the
                handle or UUID specified by ``char_specifier`` could not be found.
            backend-specific exceptions: if the read operation failed.
        """
        characteristic = _resolve_characteristic(char_specifier, self.services)
        return await self._backend.read_gatt_char(characteristic, **kwargs)

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: Buffer,
        response: Optional[bool] = None,
    ) -> None:
        r"""
        Perform a write operation on the specified GATT characteristic.

        There are two possible kinds of writes. *Write with response* (sometimes
        called a *Request*) will write the data then wait for a response from
        the remote device. *Write without response* (sometimes called *Command*)
        will queue data to be written and return immediately.

        Each characteristic may support one kind or the other or both or neither.
        Consult the device's documentation or inspect the properties of the
        characteristic to find out which kind of writes are supported.

        Args:
            char_specifier:
                The characteristic to write to, specified by either integer
                handle, UUID or directly by the :class:`~bleak.backends.characteristic.BleakGATTCharacteristic`
                object representing it. If a device has more than one characteristic
                with the same UUID, then attempting to use the UUID wil fail and
                a characteristic object must be used instead.
            data:
                The data to send. When a write-with-response operation is used,
                the length of the data is limited to 512 bytes. When a
                write-without-response operation is used, the length of the
                data is limited to :attr:`~bleak.backends.characteristic.BleakGATTCharacteristic.max_write_without_response_size`.
                Any type that supports the buffer protocol can be passed.
            response:
                If ``True``, a write-with-response operation will be used. If
                ``False``, a write-without-response operation will be used.
                Omitting the argument is deprecated and may raise a warning.
                If this arg is omitted, the default behavior is to check the
                characteristic properties to see if the "write" property is
                present. If it is, a write-with-response operation will be
                used. Note: some devices may incorrectly report or omit the
                property, which is why an explicit argument is encouraged.

        Raises:
            BleakGattCharacteristicNotFoundError: if a characteristic with the
                handle or UUID specified by ``char_specifier`` could not be found.
            backend-specific exceptions: if the write operation failed.

        .. versionchanged:: 0.21
            The default behavior when ``response=`` is omitted was changed.

        Example::

            MY_CHAR_UUID = "1234"
            ...
            await client.write_gatt_char(MY_CHAR_UUID, b"\x00\x01\x02\x03", response=True)
        """
        characteristic = _resolve_characteristic(char_specifier, self.services)

        if response is None:
            # If not specified, prefer write-with-response over write-without-
            # response if it is available since it is the more reliable write.
            # This assumes that the peripheral correctly reports the
            # characteristic properties, so doesn't work in some cases.
            response = "write" in characteristic.properties

        await self._backend.write_gatt_char(characteristic, data, response)

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[
            [BleakGATTCharacteristic, bytearray], Union[None, Awaitable[None]]
        ],
        *,
        cb: CBStartNotifyArgs = {},
        **kwargs: Any,
    ) -> None:
        """
        Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be the characteristic
        and the second will be a ``bytearray`` containing the data received.

        .. code-block:: python

            def callback(sender: BleakGATTCharacteristic, data: bytearray):
                print(f"{sender}: {data}")

            client.start_notify(char_uuid, callback)

        Args:
            char_specifier:
                The characteristic to activate notifications/indications on a
                characteristic, specified by either integer handle,
                UUID or directly by the BleakGATTCharacteristic object representing it.
            callback:
                The function to be called on notification. Can be regular
                function or async function.
            cb:
                CoreBluetooth specific arguments.

        Raises:
            BleakGattCharacteristicNotFoundError: if a characteristic with the
                handle or UUID specified by ``char_specifier`` could not be found.
            backend-specific exceptions: if the start notification operation failed.

        .. versionchanged:: 0.18
            The first argument of the callback is now a :class:`BleakGATTCharacteristic`
            instead of an ``int``.
        .. versionchanged:: 1.0
            Added the ``cb`` parameter.
        """
        if not self.is_connected:
            raise BleakError("Not connected")

        characteristic = _resolve_characteristic(char_specifier, self.services)

        if inspect.iscoroutinefunction(callback):

            def wrapped_callback(data: bytearray) -> None:
                task = asyncio.create_task(callback(characteristic, data))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)

        else:
            wrapped_callback = functools.partial(callback, characteristic)

        await self._backend.start_notify(
            characteristic, wrapped_callback, cb=cb, **kwargs
        )

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

        Raises:
            BleakGattCharacteristicNotFoundError: if a characteristic with the
                handle or UUID specified by ``char_specifier`` could not be found.
            backend-specific exceptions: if the stop notification operation failed.

        .. tip:: Notifications are stopped automatically on disconnect, so this
            method does not need to be called unless notifications need to be
            stopped some time before the device disconnects.
        """
        characteristic = _resolve_characteristic(char_specifier, self.services)
        await self._backend.stop_notify(characteristic)

    async def read_gatt_descriptor(
        self,
        desc_specifier: Union[BleakGATTDescriptor, int],
        **kwargs: Any,
    ) -> bytearray:
        """
        Perform read operation on the specified GATT descriptor.

        Args:
            desc_specifier:
                The descriptor to read from, specified by either integer handle
                or directly by the BleakGATTDescriptor object representing it.

        Raises:
            BleakError: if the descriptor could not be found.
            backend-specific exceptions: if the read operation failed.

        Returns:
            The read data.

        """
        descriptor = _resolve_descriptor(desc_specifier, self.services)
        return await self._backend.read_gatt_descriptor(descriptor, **kwargs)

    async def write_gatt_descriptor(
        self,
        desc_specifier: Union[BleakGATTDescriptor, int],
        data: Buffer,
    ) -> None:
        """
        Perform a write operation on the specified GATT descriptor.

        Args:
            desc_specifier:
                The descriptor to write to, specified by either integer handle
                directly by the BleakGATTDescriptor object representing it.
            data:
                The data to send.

        Raises:
            BleakError: if the descriptor could not be found.
            backend-specific exceptions: if the read operation failed.

        """
        descriptor = _resolve_descriptor(desc_specifier, self.services)
        await self._backend.write_gatt_descriptor(descriptor, data)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Perform Bluetooth Low Energy device scan"
    )
    parser.add_argument("-i", dest="adapter", default=None, help="HCI device")
    parser.add_argument(
        "-t", dest="timeout", type=int, default=5, help="Duration to scan for"
    )
    args = parser.parse_args()

    out = asyncio.run(
        BleakScanner.discover(adapter=args.adapter, timeout=float(args.timeout))
    )
    for o in out:
        print(str(o))


if __name__ == "__main__":
    cli()
