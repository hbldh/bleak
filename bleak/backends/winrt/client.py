# -*- coding: utf-8 -*-
"""
BLE Client for Windows 10 systems, implemented with WinRT.

Created on 2020-08-19 by hbldh <henrik.blidh@nedomkull.com>
"""

import inspect
import logging
import asyncio
import uuid
from functools import wraps
from typing import Callable, Any, List, Union

from winrt.windows.devices.enumeration import (
    DevicePairingKinds,
    DevicePairingResultStatus,
    DeviceUnpairingResultStatus,
)
from winrt.windows.security.cryptography import CryptographicBuffer

from bleak.backends.device import BLEDevice
from bleak.backends.winrt.scanner import BleakScannerWinRT
from bleak.exc import BleakError, BleakDotNetTaskError, CONTROLLER_ERROR_CODES
from bleak.backends.client import BaseBleakClient

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.winrt.service import BleakGATTServiceWinRT
from bleak.backends.winrt.characteristic import BleakGATTCharacteristicWinRT
from bleak.backends.winrt.descriptor import BleakGATTDescriptorWinRT


# Import of RT components needed.

from winrt.windows.devices.bluetooth import (
    BluetoothLEDevice,
    BluetoothConnectionStatus,
    BluetoothCacheMode,
    BluetoothAddressType,
)
from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattCommunicationStatus,
    GattWriteOption,
    GattCharacteristicProperties,
    GattClientCharacteristicConfigurationDescriptorValue,
    GattSession,
)


logger = logging.getLogger(__name__)

_communication_statues = {
    getattr(GattCommunicationStatus, k): v
    for k, v in zip(
        ["SUCCESS", "UNREACHABLE", "PROTOCOL_ERROR", "ACCESS_DENIED"],
        ["Success", "Unreachable", "ProtocolError", "AccessDenied"],
    )
}


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


class BleakClientWinRT(BaseBleakClient):
    """Native Windows Bleak Client.

    Implemented using `winrt <https://github.com/Microsoft/xlang/tree/master/src/package/pywinrt/projection>`_,
    a package that enables Python developers to access Windows Runtime APIs directly from Python.

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
        use_cached (bool): If set to `True`, then the OS level BLE cache is used for
                getting services, characteristics and descriptors. Defaults to ``True``.
        timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super(BleakClientWinRT, self).__init__(address_or_ble_device, **kwargs)

        # Backend specific. WinRT objects.
        if isinstance(address_or_ble_device, BLEDevice):
            self._device_info = address_or_ble_device.details.bluetooth_address
        else:
            self._device_info = None
        self._requester = None
        self._connect_events: List[asyncio.Event] = []
        self._disconnect_events: List[asyncio.Event] = []
        self._session: GattSession = None

        self._address_type = (
            kwargs["address_type"]
            if "address_type" in kwargs
            and kwargs["address_type"] in ("public", "random")
            else None
        )

        self._connection_status_changed_token = None
        self._use_cached = kwargs.get("use_cached", True)

    def __str__(self):
        return "BleakClientWinRT ({0})".format(self.address)

    # Connectivity methods

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.
            use_cached (bool): If set to `True`, then the OS level BLE cache is used for
                getting services, characteristics and descriptors. Defaults to ``True``.

        Returns:
            Boolean representing connection status.

        """

        # Try to find the desired device.
        timeout = kwargs.get("timeout", self._timeout)
        use_cached = kwargs.get("use_cached", self._use_cached)
        if self._device_info is None:
            device = await BleakScannerWinRT.find_device_by_address(
                self.address, timeout=timeout
            )

            if device:
                self._device_info = device.details.bluetooth_address
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

        # Called on disconnect event or on failure to connect.
        def handle_disconnect():
            if self._connection_status_changed_token:
                self._requester.remove_connection_status_changed(
                    self._connection_status_changed_token
                )
                self._connection_status_changed_token = None

            if self._requester:
                self._requester.close()
                self._requester = None

            if self._session:
                self._session.close()
                self._session = None

        def handle_connection_status_changed(
            connection_status: BluetoothConnectionStatus,
        ):
            if connection_status == BluetoothConnectionStatus.CONNECTED:
                for e in self._connect_events:
                    e.set()

            elif connection_status == BluetoothConnectionStatus.DISCONNECTED:
                if self._disconnected_callback:
                    self._disconnected_callback(self)

                for e in self._disconnect_events:
                    e.set()

                handle_disconnect()

        loop = asyncio.get_event_loop()

        def _ConnectionStatusChanged_Handler(sender, args):
            logger.debug(
                "_ConnectionStatusChanged_Handler: %d", sender.connection_status
            )
            loop.call_soon_threadsafe(
                handle_connection_status_changed, sender.connection_status
            )

        self._connection_status_changed_token = (
            self._requester.add_connection_status_changed(
                _ConnectionStatusChanged_Handler
            )
        )

        # Start a GATT Session to connect
        event = asyncio.Event()
        self._connect_events.append(event)
        try:
            self._session = await GattSession.from_device_id_async(
                self._requester.bluetooth_device_id
            )
            # This keeps the device connected until we dispose the session or
            # until we set maintain_connection = False.
            self._session.maintain_connection = True
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except BaseException:
            handle_disconnect()
            raise
        finally:
            self._connect_events.remove(event)

        # Obtain services, which also leads to connection being established.
        await self.get_services(use_cached=use_cached)

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
            self._session.close()

        # Dispose of the BluetoothLEDevice and see that the connection
        # status is now Disconnected.
        if self._requester:
            event = asyncio.Event()
            self._disconnect_events.append(event)
            try:
                self._requester.close()
                await asyncio.wait_for(event.wait(), timeout=10)
            finally:
                self._disconnect_events.remove(event)

        return True

    @property
    def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        return self._DeprecatedIsConnectedReturn(
            False
            if self._requester is None
            else self._requester.connection_status
            == BluetoothConnectionStatus.CONNECTED
        )

    @property
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        return self._session.max_pdu_size

    async def pair(self, protection_level: int = None, **kwargs) -> bool:
        """Attempts to pair with the device.

        Keyword Args:
            protection_level:
                    Windows.Devices.Enumeration.DevicePairingProtectionLevel
                        1: None - Pair the device using no levels of protection.
                        2: Encryption - Pair the device using encryption.
                        3: EncryptionAndAuthentication - Pair the device using
                           encryption and authentication. (This will not work in Bleak...)

        Returns:
            Boolean regarding success of pairing.

        """

        if (
            self._requester.device_information.pairing.can_pair
            and not self._requester.device_information.pairing.is_paired
        ):

            # Currently only supporting Just Works solutions...
            ceremony = DevicePairingKinds.CONFIRM_ONLY
            custom_pairing = self._requester.device_information.pairing.custom

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
            return self._requester.device_information.pairing.is_paired

    async def unpair(self) -> bool:
        """Attempts to unpair from the device.

        N.B. unpairing also leads to disconnection in the Windows backend.

        Returns:
            Boolean on whether the unparing was successful.

        """

        if self._requester.device_information.pairing.is_paired:
            unpairing_result = (
                await self._requester.device_information.pairing.unpair_async()
            )

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

        return not self._requester.device_information.pairing.is_paired

    # GATT services methods

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Keyword Args:

            use_cached (bool): If set to `True`, then the OS level BLE cache is used for
                getting services, characteristics and descriptors.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        use_cached = kwargs.get("use_cached", self._use_cached)
        # Return the Service Collection.
        if self._services_resolved:
            return self.services
        else:
            logger.debug("Get Services...")
            services_result = await self._requester.get_gatt_services_async(
                BluetoothCacheMode.CACHED if use_cached else BluetoothCacheMode.UNCACHED
            )

            if services_result.status != GattCommunicationStatus.SUCCESS:
                if services_result.status == GattCommunicationStatus.PROTOCOL_ERROR:
                    raise BleakDotNetTaskError(
                        "Could not get GATT services: {0} (Error: 0x{1:02X}: {2})".format(
                            _communication_statues.get(services_result.status, ""),
                            services_result.protocol_error,
                            CONTROLLER_ERROR_CODES.get(
                                services_result.protocol_error, "Unknown"
                            ),
                        )
                    )
                else:
                    raise BleakDotNetTaskError(
                        "Could not get GATT services: {0}".format(
                            _communication_statues.get(services_result.status, "")
                        )
                    )

            for service in services_result.services:
                characteristics_result = await service.get_characteristics_async(
                    BluetoothCacheMode.CACHED
                    if use_cached
                    else BluetoothCacheMode.UNCACHED
                )
                self.services.add_service(BleakGATTServiceWinRT(service))
                if characteristics_result.status != GattCommunicationStatus.SUCCESS:
                    if (
                        characteristics_result.status
                        == GattCommunicationStatus.PROTOCOL_ERROR
                    ):
                        raise BleakDotNetTaskError(
                            "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                                service,
                                _communication_statues.get(
                                    characteristics_result.status, ""
                                ),
                                characteristics_result.protocol_error,
                                CONTROLLER_ERROR_CODES.get(
                                    characteristics_result.protocol_error, "Unknown"
                                ),
                            )
                        )
                    else:
                        raise BleakDotNetTaskError(
                            "Could not get GATT characteristics for {0}: {1}".format(
                                service,
                                _communication_statues.get(
                                    characteristics_result.status, ""
                                ),
                            )
                        )
                for characteristic in characteristics_result.characteristics:
                    descriptors_result = await characteristic.get_descriptors_async(
                        BluetoothCacheMode.CACHED
                        if use_cached
                        else BluetoothCacheMode.UNCACHED
                    )
                    self.services.add_characteristic(
                        BleakGATTCharacteristicWinRT(characteristic)
                    )
                    if descriptors_result.status != GattCommunicationStatus.SUCCESS:
                        if (
                            characteristics_result.status
                            == GattCommunicationStatus.PROTOCOL_ERROR
                        ):
                            raise BleakDotNetTaskError(
                                "Could not get GATT descriptors for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                                    service,
                                    _communication_statues.get(
                                        descriptors_result.status, ""
                                    ),
                                    descriptors_result.protocol_error,
                                    CONTROLLER_ERROR_CODES.get(
                                        descriptors_result.protocol_error, "Unknown"
                                    ),
                                )
                            )
                        else:
                            raise BleakDotNetTaskError(
                                "Could not get GATT descriptors for {0}: {1}".format(
                                    characteristic,
                                    _communication_statues.get(
                                        descriptors_result.status, ""
                                    ),
                                )
                            )
                    for descriptor in list(descriptors_result.descriptors):
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
        **kwargs
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

        read_result = await characteristic.obj.read_value_async(
            BluetoothCacheMode.CACHED if use_cached else BluetoothCacheMode.UNCACHED
        )

        if read_result.status == GattCommunicationStatus.SUCCESS:
            value = bytearray(CryptographicBuffer.copy_to_byte_array(read_result.value))
            logger.debug(
                "Read Characteristic {0} : {1}".format(characteristic.uuid, value)
            )
        else:
            if read_result.status == GattCommunicationStatus.PROTOCOL_ERROR:
                raise BleakDotNetTaskError(
                    "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                        characteristic.uuid,
                        _communication_statues.get(read_result.status, ""),
                        read_result.protocol_error,
                        CONTROLLER_ERROR_CODES.get(
                            read_result.protocol_error, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not read characteristic value for {0}: {1}".format(
                        characteristic.uuid,
                        _communication_statues.get(read_result.status, ""),
                    )
                )
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

        read_result = await descriptor.obj.read_value_async(
            BluetoothCacheMode.CACHED if use_cached else BluetoothCacheMode.UNCACHED
        )

        if read_result.status == GattCommunicationStatus.SUCCESS:
            value = bytearray(CryptographicBuffer.copy_to_byte_array(read_result.value))
            logger.debug("Read Descriptor {0} : {1}".format(handle, value))
        else:
            if read_result.status == GattCommunicationStatus.PROTOCOL_ERROR:
                raise BleakDotNetTaskError(
                    "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                        descriptor.uuid,
                        _communication_statues.get(read_result.status, ""),
                        read_result.protocol_error,
                        CONTROLLER_ERROR_CODES.get(
                            read_result.protocol_error, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not read Descriptor value for {0}: {1}".format(
                        descriptor.uuid,
                        _communication_statues.get(read_result.status, ""),
                    )
                )

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
        write_result = await characteristic.obj.write_value_with_result_async(
            CryptographicBuffer.create_from_byte_array(list(data)), response
        )

        if write_result.status == GattCommunicationStatus.SUCCESS:
            logger.debug(
                "Write Characteristic {0} : {1}".format(characteristic.uuid, data)
            )
        else:
            if write_result.status == GattCommunicationStatus.PROTOCOL_ERROR:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2} (Error: 0x{3:02X}: {4})".format(
                        data,
                        characteristic.uuid,
                        _communication_statues.get(write_result.status, ""),
                        write_result.protocol_error,
                        CONTROLLER_ERROR_CODES.get(
                            write_result.protocol_error, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2}".format(
                        data,
                        characteristic.uuid,
                        _communication_statues.get(write_result.status, ""),
                    )
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

        write_result = await descriptor.obj.write_value_async(
            CryptographicBuffer.create_from_byte_array(list(data))
        )

        if write_result.status == GattCommunicationStatus.SUCCESS:
            logger.debug("Write Descriptor {0} : {1}".format(handle, data))
        else:
            if write_result.status == GattCommunicationStatus.PROTOCOL_ERROR:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2} (Error: 0x{3:02X}: {4})".format(
                        data,
                        descriptor.uuid,
                        _communication_statues.get(write_result.status, ""),
                        write_result.protocol_error,
                        CONTROLLER_ERROR_CODES.get(
                            write_result.protocol_error, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not write value {0} to descriptor {1}: {2}".format(
                        data,
                        descriptor.uuid,
                        _communication_statues.get(write_result.status, ""),
                    )
                )

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs
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
        if (
            characteristic_obj.characteristic_properties
            & GattCharacteristicProperties.INDICATE
        ):
            cccd = GattClientCharacteristicConfigurationDescriptorValue.INDICATE
        elif (
            characteristic_obj.characteristic_properties
            & GattCharacteristicProperties.NOTIFY
        ):
            cccd = GattClientCharacteristicConfigurationDescriptorValue.NOTIFY
        else:
            cccd = GattClientCharacteristicConfigurationDescriptorValue.NONE

        fcn = _notification_wrapper(bleak_callback, asyncio.get_event_loop())
        event_handler_token = characteristic_obj.add_value_changed(fcn)
        self._notification_callbacks[characteristic.handle] = event_handler_token
        status = await characteristic_obj.write_client_characteristic_configuration_descriptor_async(
            cccd
        )

        if status != GattCommunicationStatus.SUCCESS:
            # This usually happens when a device reports that it supports indicate,
            # but it actually doesn't.
            if characteristic.handle in self._notification_callbacks:
                event_handler_token = self._notification_callbacks.pop(
                    characteristic.handle
                )
                characteristic_obj.remove_value_changed(event_handler_token)

            raise BleakError(
                "Could not start notify on {0}: {1}".format(
                    characteristic.uuid, _communication_statues.get(status, "")
                )
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
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} not found!".format(char_specifier))

        status = await characteristic.obj.write_client_characteristic_configuration_descriptor_async(
            GattClientCharacteristicConfigurationDescriptorValue.NONE
        )

        if status != GattCommunicationStatus.SUCCESS:
            raise BleakError(
                "Could not stop notify on {0}: {1}".format(
                    characteristic.uuid, _communication_statues.get(status, "")
                )
            )
        else:
            event_handler_token = self._notification_callbacks.pop(
                characteristic.handle
            )
            characteristic.obj.remove_value_changed(event_handler_token)


def _notification_wrapper(func: Callable, loop: asyncio.AbstractEventLoop):
    @wraps(func)
    def dotnet_notification_parser(sender: Any, args: Any):
        # Return only the UUID string representation as sender.
        # Also do a conversion from System.Bytes[] to bytearray.
        value = bytearray(
            CryptographicBuffer.copy_to_byte_array(args.characteristic_value)
        )

        return loop.call_soon_threadsafe(func, sender.attribute_handle, value)

    return dotnet_notification_parser
