# -*- coding: utf-8 -*-
"""
BLE Client for Windows 10 systems, implemented with WinRT.

Created on 2020-08-19 by hbldh <henrik.blidh@nedomkull.com>
"""

import inspect
import logging
import asyncio
from typing_extensions import Literal, TypedDict
import uuid
import warnings
from functools import wraps
from typing import Callable, Any, List, Optional, Sequence, Union

from bleak_winrt.windows.devices.bluetooth import (
    BluetoothError,
    BluetoothLEDevice,
    BluetoothCacheMode,
    BluetoothAddressType,
)
from bleak_winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattCharacteristic,
    GattCommunicationStatus,
    GattDescriptor,
    GattDeviceService,
    GattSessionStatus,
    GattSessionStatusChangedEventArgs,
    GattWriteOption,
    GattCharacteristicProperties,
    GattClientCharacteristicConfigurationDescriptorValue,
    GattSession,
)
from bleak_winrt.windows.devices.enumeration import (
    DeviceInformation,
    DevicePairingKinds,
    DevicePairingResultStatus,
    DeviceUnpairingResultStatus,
)
from bleak_winrt.windows.foundation import EventRegistrationToken
from bleak_winrt.windows.storage.streams import Buffer

from bleak.backends.device import BLEDevice
from bleak.backends.winrt.scanner import BleakScannerWinRT
from bleak.exc import BleakError, PROTOCOL_ERROR_CODES
from bleak.backends.client import BaseBleakClient

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.winrt.service import BleakGATTServiceWinRT
from bleak.backends.winrt.characteristic import BleakGATTCharacteristicWinRT
from bleak.backends.winrt.descriptor import BleakGATTDescriptorWinRT


logger = logging.getLogger(__name__)

_ACCESS_DENIED_SERVICES = list(
    uuid.UUID(u)
    for u in ("00001812-0000-1000-8000-00805f9b34fb",)  # Human Interface Device Service
)

_pairing_statuses = {
    getattr(DevicePairingResultStatus, v): v
    for v in dir(DevicePairingResultStatus)
    if "_" not in v and isinstance(getattr(DevicePairingResultStatus, v), int)
}


_unpairing_statuses = {
    getattr(DeviceUnpairingResultStatus, v): v
    for v in dir(DeviceUnpairingResultStatus)
    if "_" not in v and isinstance(getattr(DeviceUnpairingResultStatus, v), int)
}

# TODO: we can use this when minimum Python is 3.8
# class _Result(typing.Protocol):
#     status: GattCommunicationStatus
#     protocol_error: typing.Optional[int]


def _ensure_success(result: Any, attr: Optional[str], fail_msg: str) -> Any:
    """
    Ensures that *status* is ``GattCommunicationStatus.SUCCESS``, otherwise
    raises ``BleakError``.

    Args:
        result: The result returned by a WinRT API method.
        attr: The name of the attribute containing the result.
        fail_msg: A message to include in the exception.
    """
    status = result.status if hasattr(result, "status") else result

    if status == GattCommunicationStatus.SUCCESS:
        return None if attr is None else getattr(result, attr)

    if status == GattCommunicationStatus.PROTOCOL_ERROR:
        err = PROTOCOL_ERROR_CODES.get(result.protocol_error, "Unknown")
        raise BleakError(
            f"{fail_msg}: Protocol Error 0x{result.protocol_error:02X}: {err}"
        )

    if status == GattCommunicationStatus.ACCESS_DENIED:
        raise BleakError(f"{fail_msg}: Access Denied")

    if status == GattCommunicationStatus.UNREACHABLE:
        raise BleakError(f"{fail_msg}: Unreachable")

    raise BleakError(f"{fail_msg}: Unexpected status code 0x{result.status:02X}")


class WinRTClientArgs(TypedDict, total=False):
    """
    Windows-specific arguments for :class:`BleakClient`.
    """

    address_type: Literal["public", "random"]
    """
    Can either be ``"public"`` or ``"random"``, depending on the required address
    type needed to connect to your device.
    """

    use_cached_services: bool
    """
    ``True`` allows Windows to fetch the services, characteristics and descriptors
    from the Windows cache instead of reading them from the device. Can be very
    much faster for known, unchanging devices, but not recommended for DIY peripherals
    where the GATT layout can change between connections.

    ``False`` will force the attribute database to be read from the remote device
    instead of using the OS cache.

    If omitted, the OS Bluetooth stack will do what it thinks is best.
    """


class BleakClientWinRT(BaseBleakClient):
    """Native Windows Bleak Client.

    Implemented using `winrt <https://github.com/Microsoft/xlang/tree/master/src/package/pywinrt/projection>`_,
    a package that enables Python developers to access Windows Runtime APIs directly from Python.

    Args:
        address_or_ble_device (str or BLEDevice): The Bluetooth address of the BLE peripheral
            to connect to or the ``BLEDevice`` object representing it.
        winrt (dict): A dictionary of Windows-specific configuration values.
        **timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.
        **disconnected_callback (callable): Callback that will be scheduled in the
            event loop when the client is disconnected. The callable must take one
            argument, which will be this client object.
    """

    def __init__(
        self,
        address_or_ble_device: Union[BLEDevice, str],
        *,
        winrt: WinRTClientArgs = {},
        **kwargs,
    ):
        super(BleakClientWinRT, self).__init__(address_or_ble_device, **kwargs)

        # Backend specific. WinRT objects.
        if isinstance(address_or_ble_device, BLEDevice):
            self._device_info = address_or_ble_device.details.adv.bluetooth_address
        else:
            self._device_info = None
        self._requester = None
        self._session_active_events: List[asyncio.Event] = []
        self._session_closed_events: List[asyncio.Event] = []
        self._session: GattSession = None

        if "address_type" in kwargs:
            warnings.warn(
                "The address_type keyword arg will in a future version be moved into the win dict input instead.",
                PendingDeprecationWarning,
                stacklevel=2,
            )

        # os-specific options
        self._use_cached_services = winrt.get("use_cached_services")
        self._address_type = winrt.get("address_type", kwargs.get("address_type"))

        self._session_status_changed_token: Optional[EventRegistrationToken] = None

    def __str__(self):
        return "BleakClientWinRT ({0})".format(self.address)

    # Connectivity methods

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

        Returns:
            Boolean representing connection status.

        """
        # Try to find the desired device.
        timeout = kwargs.get("timeout", self._timeout)
        if self._device_info is None:
            device = await BleakScannerWinRT.find_device_by_address(
                self.address, timeout=timeout
            )

            if device:
                self._device_info = device.details.adv.bluetooth_address
            else:
                raise BleakError(
                    "Device with address {0} was not found.".format(self.address)
                )

        logger.debug("Connecting to BLE device @ {0}".format(self.address))

        args = [
            self._device_info,
        ]
        if self._address_type is not None:
            args.append(
                BluetoothAddressType.PUBLIC
                if self._address_type == "public"
                else BluetoothAddressType.RANDOM
            )
        self._requester = await BluetoothLEDevice.from_bluetooth_address_async(*args)

        if self._requester is None:
            # https://github.com/microsoft/Windows-universal-samples/issues/1089#issuecomment-487586755
            raise BleakError(
                f"Failed to connect to {self._device_info}. If the device requires pairing, then pair first. If the device uses a random address, it may have changed."
            )

        # Called on disconnect event or on failure to connect.
        def handle_disconnect():
            if self._session_status_changed_token:
                self._session.remove_session_status_changed(
                    self._session_status_changed_token
                )
                self._session_status_changed_token = None

            if self._requester:
                self._requester.close()
                self._requester = None

            if self._session:
                self._session.close()
                self._session = None

        def handle_session_status_changed(
            args: GattSessionStatusChangedEventArgs,
        ):
            if args.error != BluetoothError.SUCCESS:
                logger.error(f"Unhandled GATT error {args.error}")

            if args.status == GattSessionStatus.ACTIVE:
                for e in self._session_active_events:
                    e.set()

            elif args.status == GattSessionStatus.CLOSED:
                if self._disconnected_callback:
                    self._disconnected_callback(self)

                for e in self._session_closed_events:
                    e.set()

                handle_disconnect()

        loop = asyncio.get_running_loop()

        # this is the WinRT event handler will be called on another thread
        def session_status_changed_event_handler(
            sender: GattSession, args: GattSessionStatusChangedEventArgs
        ):
            logger.debug(
                "session_status_changed_event_handler: id: %s, error: %s, status: %s",
                sender.device_id,
                args.error,
                args.status,
            )
            loop.call_soon_threadsafe(handle_session_status_changed, args)

        # Start a GATT Session to connect
        event = asyncio.Event()
        self._session_active_events.append(event)
        try:
            self._session = await GattSession.from_device_id_async(
                self._requester.bluetooth_device_id
            )

            if not self._session.can_maintain_connection:
                raise BleakError("device does not support GATT sessions")

            self._session_status_changed_token = (
                self._session.add_session_status_changed(
                    session_status_changed_event_handler
                )
            )

            # Windows does not support explicitly connecting to a device.
            # Instead it has the concept of a GATT session that is owned
            # by the calling program.
            self._session.maintain_connection = True
            # This keeps the device connected until we set maintain_connection = False.

            # wait for the session to become active
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except BaseException:
            handle_disconnect()
            raise
        finally:
            self._session_active_events.remove(event)

        # Obtain services, which also leads to connection being established.
        await self.get_services()

        return True

    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Boolean representing if device is disconnected.

        """
        logger.debug("Disconnecting from BLE device...")
        # Remove notifications.
        for handle, event_handler_token in list(self._notification_callbacks.items()):
            char = self.services.get_characteristic(handle)
            char.obj.remove_value_changed(event_handler_token)
        self._notification_callbacks.clear()

        # Dispose all service components that we have requested and created.
        for service in self.services:
            service.obj.close()
        self.services = BleakGATTServiceCollection()
        self._services_resolved = False

        # Without this, disposing the BluetoothLEDevice won't disconnect it
        if self._session:
            self._session.maintain_connection = False
            # calling self._session.close() here prevents any further GATT
            # session status events, so we defer that until after the session
            # is no longer active

        # Dispose of the BluetoothLEDevice and see that the session
        # status is now closed.
        if self._requester:
            event = asyncio.Event()
            self._session_closed_events.append(event)
            try:
                self._requester.close()
                await asyncio.wait_for(event.wait(), timeout=10)
            finally:
                self._session_closed_events.remove(event)

        return True

    @property
    def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        return self._DeprecatedIsConnectedReturn(
            False
            if self._session is None
            else self._session.session_status == GattSessionStatus.ACTIVE
        )

    @property
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        return self._session.max_pdu_size

    async def pair(self, protection_level: int = None, **kwargs) -> bool:
        """Attempts to pair with the device.

        Keyword Args:
            protection_level (int): A ``DevicePairingProtectionLevel`` enum value:

                1. None - Pair the device using no levels of protection.
                2. Encryption - Pair the device using encryption.
                3. EncryptionAndAuthentication - Pair the device using
                   encryption and authentication. (This will not work in Bleak...)

        Returns:
            Boolean regarding success of pairing.

        """
        # New local device information object created since the object from the requester isn't updated
        device_information = await DeviceInformation.create_from_id_async(
            self._requester.device_information.id
        )
        if (
            device_information.pairing.can_pair
            and not device_information.pairing.is_paired
        ):

            # Currently only supporting Just Works solutions...
            ceremony = DevicePairingKinds.CONFIRM_ONLY
            custom_pairing = device_information.pairing.custom

            def handler(sender, args):
                args.accept()

            pairing_requested_token = custom_pairing.add_pairing_requested(handler)
            try:
                if protection_level:
                    pairing_result = await custom_pairing.pair_async(
                        ceremony, protection_level
                    )
                else:
                    pairing_result = await custom_pairing.pair_async(ceremony)

            except Exception as e:
                raise BleakError("Failure trying to pair with device!") from e
            finally:
                custom_pairing.remove_pairing_requested(pairing_requested_token)

            if pairing_result.status not in (
                DevicePairingResultStatus.PAIRED,
                DevicePairingResultStatus.ALREADY_PAIRED,
            ):
                raise BleakError(
                    "Could not pair with device: {0}: {1}".format(
                        pairing_result.status,
                        _pairing_statuses.get(pairing_result.status),
                    )
                )
            else:
                logger.info(
                    "Paired to device with protection level {0}.".format(
                        pairing_result.protection_level_used
                    )
                )
                return True
        else:
            return device_information.pairing.is_paired

    async def unpair(self) -> bool:
        """Attempts to unpair from the device.

        N.B. unpairing also leads to disconnection in the Windows backend.

        Returns:
            Boolean on whether the unparing was successful.

        """

        # New local device information object created since the object from the requester isn't updated
        device_information = await DeviceInformation.create_from_id_async(
            self._requester.device_information.id
        )
        if device_information.pairing.is_paired:
            unpairing_result = await device_information.pairing.unpair_async()

            if unpairing_result.status not in (
                DevicePairingResultStatus.PAIRED,
                DevicePairingResultStatus.ALREADY_PAIRED,
            ):
                raise BleakError(
                    "Could not unpair with device: {0}: {1}".format(
                        unpairing_result.status,
                        _unpairing_statuses.get(unpairing_result.status),
                    )
                )
            else:
                logger.info("Unpaired with device.")
                return True

        return not device_information.pairing.is_paired

    # GATT services methods

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        # Return the Service Collection.
        if self._services_resolved:
            return self.services
        else:
            logger.debug("Get Services...")

            # Each of the get_serv/char/desc_async() methods has two forms, one
            # with no args and one with a cache_mode argument
            args = []

            # If the os-specific use_cached_services arg was given when BleakClient
            # was created, the we use the second form with explicit cache mode.
            # Otherwise we use the first form with no explicit cache mode which
            # allows the OS Bluetooth stack to decide what is best.
            if self._use_cached_services is not None:
                args.append(
                    BluetoothCacheMode.CACHED
                    if self._use_cached_services
                    else BluetoothCacheMode.UNCACHED
                )

            services: Sequence[GattDeviceService] = _ensure_success(
                await self._requester.get_gatt_services_async(*args),
                "services",
                "Could not get GATT services",
            )

            for service in services:
                # Windows returns an ACCESS_DENIED error when trying to enumerate
                # characteristics of services used by the OS, like the HID service
                # so we have to exclude those services.
                if service.uuid in _ACCESS_DENIED_SERVICES:
                    continue

                self.services.add_service(BleakGATTServiceWinRT(service))

                characteristics: Sequence[GattCharacteristic] = _ensure_success(
                    await service.get_characteristics_async(*args),
                    "characteristics",
                    f"Could not get GATT characteristics for {service}",
                )

                for characteristic in characteristics:
                    self.services.add_characteristic(
                        BleakGATTCharacteristicWinRT(characteristic)
                    )

                    descriptors: Sequence[GattDescriptor] = _ensure_success(
                        await characteristic.get_descriptors_async(*args),
                        "descriptors",
                        f"Could not get GATT descriptors for {service}",
                    )

                    for descriptor in descriptors:
                        self.services.add_descriptor(
                            BleakGATTDescriptorWinRT(
                                descriptor,
                                str(characteristic.uuid),
                                characteristic.attribute_handle,
                            )
                        )

            logger.info("Services resolved for %s", str(self))
            self._services_resolved = True
            return self.services

    # I/O methods

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

        Keyword Args:
            use_cached (bool): ``False`` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to ``False``.

        Returns:
            (bytearray) The read data.

        """
        use_cached = kwargs.get("use_cached", False)

        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {0} was not found!".format(char_specifier))

        value = bytearray(
            _ensure_success(
                await characteristic.obj.read_value_async(
                    BluetoothCacheMode.CACHED
                    if use_cached
                    else BluetoothCacheMode.UNCACHED
                ),
                "value",
                f"Could not read characteristic handle {characteristic.handle}",
            )
        )

        logger.debug(f"Read Characteristic {characteristic.handle:04X} : {value}")

        return value

    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.

        Keyword Args:
            use_cached (bool): `False` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.

        """
        use_cached = kwargs.get("use_cached", False)

        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))

        value = bytearray(
            _ensure_success(
                await descriptor.obj.read_value_async(
                    BluetoothCacheMode.CACHED
                    if use_cached
                    else BluetoothCacheMode.UNCACHED
                ),
                "value",
                f"Could not read Descriptor value for {handle:04X}",
            )
        )

        logger.debug(f"Read Descriptor {handle:04X} : {value}")

        return value

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: Union[bytes, bytearray, memoryview],
        response: bool = False,
    ) -> None:
        """Perform a write operation of the specified GATT characteristic.

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to write
                to, specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristic object representing it.
            data (bytes or bytearray): The data to send.
            response (bool): If write-with-response operation should be done. Defaults to `False`.

        """
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))

        response = (
            GattWriteOption.WRITE_WITH_RESPONSE
            if response
            else GattWriteOption.WRITE_WITHOUT_RESPONSE
        )
        buf = Buffer(len(data))
        buf.length = buf.capacity
        with memoryview(buf) as mv:
            mv[:] = data
        _ensure_success(
            await characteristic.obj.write_value_with_result_async(buf, response),
            None,
            f"Could not write value {data} to characteristic {characteristic.handle:04X}",
        )

    async def write_gatt_descriptor(
        self, handle: int, data: Union[bytes, bytearray, memoryview]
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            data (bytes or bytearray): The data to send.

        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))

        buf = Buffer(len(data))
        buf.length = buf.capacity
        with memoryview(buf) as mv:
            mv[:] = data
        _ensure_success(
            await descriptor.obj.write_value_with_result_async(buf),
            None,
            f"Could not write value {data} to descriptor {handle:04X}",
        )

        logger.debug(f"Write Descriptor {handle:04X} : {data}")

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs,
    ) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be a uuid string
        object and the second will be a bytearray.

        .. code-block:: python

            def callback(sender, data):
                print(f"{sender}: {data}")
            client.start_notify(char_uuid, callback)

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to activate
                notifications/indications on a characteristic, specified by either integer handle,
                UUID or directly by the BleakGATTCharacteristic object representing it.
            callback (function): The function to be called on notification.

        Keyword Args:
            force_indicate (bool): If this is set to True, then Bleak will set up a indication request instead of a
                notification request, given that the characteristic supports notifications as well as indications.

        """
        if inspect.iscoroutinefunction(callback):

            def bleak_callback(s, d):
                asyncio.ensure_future(callback(s, d))

        else:
            bleak_callback = callback

        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {0} not found!".format(char_specifier))

        if self._notification_callbacks.get(characteristic.handle):
            await self.stop_notify(characteristic)

        characteristic_obj = characteristic.obj

        # If we want to force indicate even when notify is available, also check if the device
        # actually supports indicate as well.
        if not kwargs.get("force_indicate", False) and (
            characteristic_obj.characteristic_properties
            & GattCharacteristicProperties.NOTIFY
        ):
            cccd = GattClientCharacteristicConfigurationDescriptorValue.NOTIFY
        elif (
            characteristic_obj.characteristic_properties
            & GattCharacteristicProperties.INDICATE
        ):
            cccd = GattClientCharacteristicConfigurationDescriptorValue.INDICATE
        else:
            raise BleakError(
                "characteristic does not support notifications or indications"
            )

        fcn = _notification_wrapper(bleak_callback, asyncio.get_running_loop())
        event_handler_token = characteristic_obj.add_value_changed(fcn)
        self._notification_callbacks[characteristic.handle] = event_handler_token
        try:
            _ensure_success(
                await characteristic_obj.write_client_characteristic_configuration_descriptor_async(
                    cccd
                ),
                None,
                f"Could not start notify on {characteristic.handle:04X}",
            )
        except BaseException:

            # This usually happens when a device reports that it supports indicate,
            # but it actually doesn't.
            if characteristic.handle in self._notification_callbacks:
                event_handler_token = self._notification_callbacks.pop(
                    characteristic.handle
                )
                characteristic_obj.remove_value_changed(event_handler_token)

            raise

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
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} not found!".format(char_specifier))

        _ensure_success(
            await characteristic.obj.write_client_characteristic_configuration_descriptor_async(
                GattClientCharacteristicConfigurationDescriptorValue.NONE
            ),
            None,
            f"Could not stop notify on {characteristic.handle:04X}",
        )

        event_handler_token = self._notification_callbacks.pop(characteristic.handle)
        characteristic.obj.remove_value_changed(event_handler_token)


def _notification_wrapper(func: Callable, loop: asyncio.AbstractEventLoop):
    @wraps(func)
    def notification_parser(sender: Any, args: Any):
        # Return only the UUID string representation as sender.
        # Also do a conversion from System.Bytes[] to bytearray.
        value = bytearray(args.characteristic_value)

        return loop.call_soon_threadsafe(func, sender.attribute_handle, value)

    return notification_parser
