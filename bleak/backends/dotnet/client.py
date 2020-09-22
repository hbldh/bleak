# -*- coding: utf-8 -*-
"""
BLE Client for Windows 10 systems.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>
"""

import logging
import asyncio
import uuid
from functools import wraps
from typing import Callable, Any, Union

from bleak.backends.device import BLEDevice
from bleak.backends.dotnet.scanner import BleakScannerDotNet
from bleak.exc import BleakError, BleakDotNetTaskError, CONTROLLER_ERROR_CODES
from bleak.backends.client import BaseBleakClient
from bleak.backends.dotnet.utils import (
    BleakDataReader,
    BleakDataWriter,
    wrap_IAsyncOperation,
)

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.dotnet.service import BleakGATTServiceDotNet
from bleak.backends.dotnet.characteristic import BleakGATTCharacteristicDotNet
from bleak.backends.dotnet.descriptor import BleakGATTDescriptorDotNet


# CLR imports
# Import of Bleak CLR->UWP Bridge.
from BleakBridge import Bridge

# Import of other CLR components needed.
from System import UInt64, Object
from Windows.Foundation import IAsyncOperation, TypedEventHandler
from Windows.Storage.Streams import DataReader, DataWriter, IBuffer
from Windows.Devices.Enumeration import (
    DevicePairingResult,
    DevicePairingResultStatus,
    DeviceUnpairingResult,
    DeviceUnpairingResultStatus,
    DevicePairingKinds,
    DevicePairingProtectionLevel,
    DeviceInformationCustomPairing,
    DevicePairingRequestedEventArgs,
)
from Windows.Devices.Bluetooth import (
    BluetoothLEDevice,
    BluetoothConnectionStatus,
    BluetoothCacheMode,
    BluetoothAddressType,
)
from Windows.Devices.Bluetooth.GenericAttributeProfile import (
    GattDeviceService,
    GattDeviceServicesResult,
    GattCharacteristic,
    GattCharacteristicsResult,
    GattDescriptor,
    GattDescriptorsResult,
    GattCommunicationStatus,
    GattReadResult,
    GattWriteOption,
    GattWriteResult,
    GattValueChangedEventArgs,
    GattCharacteristicProperties,
    GattClientCharacteristicConfigurationDescriptorValue,
)

logger = logging.getLogger(__name__)

_communication_statues = {
    getattr(GattCommunicationStatus, k): k
    for k in ["Success", "Unreachable", "ProtocolError", "AccessDenied"]
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


class BleakClientDotNet(BaseBleakClient):
    """The native Windows Bleak Client.

    Implemented using `pythonnet <https://pythonnet.github.io/>`_, a package that provides an integration to the .NET
    Common Language Runtime (CLR). Therefore, much of the code below has a distinct C# feel.

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super(BleakClientDotNet, self).__init__(address_or_ble_device, **kwargs)

        # Backend specific. Python.NET objects.
        if isinstance(address_or_ble_device, BLEDevice):
            self._device_info = address_or_ble_device.details.BluetoothAddress
        else:
            self._device_info = None
        self._requester = None
        self._bridge = None

        self._address_type = (
            kwargs["address_type"]
            if "address_type" in kwargs
            and kwargs["address_type"] in ("public", "random")
            else None
        )

    def __str__(self):
        return "BleakClientDotNet ({0})".format(self.address)

    # Connectivity methods

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

        Returns:
            Boolean representing connection status.

        """
        # Create a new BleakBridge here.
        self._bridge = Bridge()

        # Try to find the desired device.
        if self._device_info is None:
            timeout = kwargs.get("timeout", self._timeout)
            device = await BleakScannerDotNet.find_device_by_address(
                self.address, timeout=timeout
            )

            if device:
                self._device_info = device.details.BluetoothAddress
            else:
                raise BleakError(
                    "Device with address {0} was not found.".format(self.address)
                )

        logger.debug("Connecting to BLE device @ {0}".format(self.address))

        args = [UInt64(self._device_info)]
        if self._address_type is not None:
            args.append(
                BluetoothAddressType.Public
                if self._address_type == "public"
                else BluetoothAddressType.Random
            )
        self._requester = await wrap_IAsyncOperation(
            IAsyncOperation[BluetoothLEDevice](
                BluetoothLEDevice.FromBluetoothAddressAsync(*args)
            ),
            return_type=BluetoothLEDevice,
        )

        loop = asyncio.get_event_loop()

        def _ConnectionStatusChanged_Handler(sender, args):
            logger.debug(
                "_ConnectionStatusChanged_Handler: %d", sender.ConnectionStatus
            )
            if (
                sender.ConnectionStatus == BluetoothConnectionStatus.Disconnected
                and self._disconnected_callback
            ):
                loop.call_soon_threadsafe(self._disconnected_callback, self)

        self._requester.ConnectionStatusChanged += _ConnectionStatusChanged_Handler

        # Obtain services, which also leads to connection being established.
        services = await self.get_services()
        connected = False
        if self._services_resolved:
            # If services has been resolved, then we assume that we are connected. This is due to
            # some issues with getting `is_connected` to give correct response here.
            connected = True
        else:
            for _ in range(5):
                await asyncio.sleep(0.2)
                connected = await self.is_connected()
                if connected:
                    break

        if connected:
            logger.debug("Connection successful.")
        else:
            raise BleakError(
                "Connection to {0} was not successful!".format(self.address)
            )

        return connected

    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Boolean representing if device is disconnected.

        """
        logger.debug("Disconnecting from BLE device...")
        # Remove notifications. Remove them first in the BleakBridge and then clear
        # remaining notifications in Python as well.
        for characteristic in self.services.characteristics.values():
            self._bridge.RemoveValueChangedCallback(characteristic.obj)
        self._notification_callbacks.clear()

        # Dispose all service components that we have requested and created.
        for service in self.services:
            service.obj.Dispose()
        self.services = BleakGATTServiceCollection()
        self._services_resolved = False

        # Dispose of the BluetoothLEDevice and see that the connection
        # status is now Disconnected.
        self._requester.Dispose()
        is_disconnected = (
            self._requester.ConnectionStatus == BluetoothConnectionStatus.Disconnected
        )
        self._requester = None

        # Set device info to None as well.
        self._device_info = None

        # Finally, dispose of the Bleak Bridge as well.
        self._bridge.Dispose()
        self._bridge = None

        return is_disconnected

    async def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        if self._requester:
            return (
                self._requester.ConnectionStatus == BluetoothConnectionStatus.Connected
            )
        else:
            return False

    async def pair(self, protection_level=None, **kwargs) -> bool:
        """Attempts to pair with the device.

        Keyword Args:
            protection_level:
                    DevicePairingProtectionLevel
                        1: None - Pair the device using no levels of protection.
                        2: Encryption - Pair the device using encryption.
                        3: EncryptionAndAuthentication - Pair the device using encryption and authentication.

        Returns:
            Boolean regarding success of pairing.

        """
        if (
            self._requester.DeviceInformation.Pairing.CanPair
            and not self._requester.DeviceInformation.Pairing.IsPaired
        ):

            # Currently only supporting Just Works solutions...
            ceremony = DevicePairingKinds.ConfirmOnly
            custom_pairing = self._requester.DeviceInformation.Pairing.Custom

            def handler(sender, args):
                args.Accept()

            custom_pairing.PairingRequested += handler

            if protection_level:
                raise NotImplementedError(
                    "Cannot set minimally required protection level yet..."
                )
            else:
                pairing_result = await wrap_IAsyncOperation(
                    IAsyncOperation[DevicePairingResult](
                        custom_pairing.PairAsync.Overloads[DevicePairingKinds](ceremony)
                    ),
                    return_type=DevicePairingResult,
                )

            try:
                custom_pairing.PairingRequested -= handler
            except Exception as e:
                # TODO: Find a way to remove WinRT events...
                pass
            finally:
                del handler

            if pairing_result.Status not in (
                DevicePairingResultStatus.Paired,
                DevicePairingResultStatus.AlreadyPaired,
            ):
                raise BleakError(
                    "Could not pair with device: {0}: {1}".format(
                        pairing_result.Status,
                        _pairing_statuses.get(pairing_result.Status),
                    )
                )
            else:
                logger.info(
                    "Paired to device with protection level {0}.".format(
                        pairing_result.ProtectionLevelUsed
                    )
                )

        return self._requester.DeviceInformation.Pairing.IsPaired

    async def unpair(self) -> bool:
        """Attempts to unpair from the device.

        Returns:
            Boolean on whether the unparing was successful.

        """

        if self._requester.DeviceInformation.Pairing.IsPaired:
            unpairing_result = await wrap_IAsyncOperation(
                IAsyncOperation[DeviceUnpairingResult](
                    self._requester.DeviceInformation.Pairing.UnpairAsync()
                ),
                return_type=DeviceUnpairingResult,
            )

            if unpairing_result.Status not in (
                DevicePairingResultStatus.Paired,
                DevicePairingResultStatus.AlreadyPaired,
            ):
                raise BleakError(
                    "Could not unpair with device: {0}: {1}".format(
                        unpairing_result.Status,
                        _unpairing_statuses.get(unpairing_result.Status),
                    )
                )
            else:
                logger.info("Unpaired with device.")

        return not self._requester.DeviceInformation.Pairing.IsPaired

    # GATT services methods

    async def get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        # Return the Service Collection.
        if self._services_resolved:
            return self.services
        else:
            logger.debug("Get Services...")
            services_result = await wrap_IAsyncOperation(
                IAsyncOperation[GattDeviceServicesResult](
                    self._requester.GetGattServicesAsync()
                ),
                return_type=GattDeviceServicesResult,
            )

            if services_result.Status != GattCommunicationStatus.Success:
                if services_result.Status == GattCommunicationStatus.ProtocolError:
                    raise BleakDotNetTaskError(
                        "Could not get GATT services: {0} (Error: 0x{1:02X}: {2})".format(
                            _communication_statues.get(services_result.Status, ""),
                            services_result.ProtocolError,
                            CONTROLLER_ERROR_CODES.get(
                                services_result.ProtocolError, "Unknown"
                            ),
                        )
                    )
                else:
                    raise BleakDotNetTaskError(
                        "Could not get GATT services: {0}".format(
                            _communication_statues.get(services_result.Status, "")
                        )
                    )

            for service in services_result.Services:
                characteristics_result = await wrap_IAsyncOperation(
                    IAsyncOperation[GattCharacteristicsResult](
                        service.GetCharacteristicsAsync()
                    ),
                    return_type=GattCharacteristicsResult,
                )
                self.services.add_service(BleakGATTServiceDotNet(service))
                if characteristics_result.Status != GattCommunicationStatus.Success:
                    if (
                        characteristics_result.Status
                        == GattCommunicationStatus.ProtocolError
                    ):
                        raise BleakDotNetTaskError(
                            "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                                service,
                                _communication_statues.get(
                                    characteristics_result.Status, ""
                                ),
                                characteristics_result.ProtocolError,
                                CONTROLLER_ERROR_CODES.get(
                                    characteristics_result.ProtocolError, "Unknown"
                                ),
                            )
                        )
                    else:
                        raise BleakDotNetTaskError(
                            "Could not get GATT characteristics for {0}: {1}".format(
                                service,
                                _communication_statues.get(
                                    characteristics_result.Status, ""
                                ),
                            )
                        )
                for characteristic in characteristics_result.Characteristics:
                    descriptors_result = await wrap_IAsyncOperation(
                        IAsyncOperation[GattDescriptorsResult](
                            characteristic.GetDescriptorsAsync()
                        ),
                        return_type=GattDescriptorsResult,
                    )
                    self.services.add_characteristic(
                        BleakGATTCharacteristicDotNet(characteristic)
                    )
                    if descriptors_result.Status != GattCommunicationStatus.Success:
                        if (
                            characteristics_result.Status
                            == GattCommunicationStatus.ProtocolError
                        ):
                            raise BleakDotNetTaskError(
                                "Could not get GATT descriptors for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                                    service,
                                    _communication_statues.get(
                                        descriptors_result.Status, ""
                                    ),
                                    descriptors_result.ProtocolError,
                                    CONTROLLER_ERROR_CODES.get(
                                        descriptors_result.ProtocolError, "Unknown"
                                    ),
                                )
                            )
                        else:
                            raise BleakDotNetTaskError(
                                "Could not get GATT descriptors for {0}: {1}".format(
                                    characteristic,
                                    _communication_statues.get(
                                        descriptors_result.Status, ""
                                    ),
                                )
                            )
                    for descriptor in list(descriptors_result.Descriptors):
                        self.services.add_descriptor(
                            BleakGATTDescriptorDotNet(
                                descriptor,
                                characteristic.Uuid.ToString(),
                                int(characteristic.AttributeHandle),
                            )
                        )

            logger.info("Services resolved for %s", str(self))
            self._services_resolved = True
            return self.services

    # I/O methods

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        use_cached=False,
        **kwargs
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            char_specifier (BleakGATTCharacteristic, int, str or UUID): The characteristic to read from,
                specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristic object representing it.
            use_cached (bool): `False` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.

        """
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {0} was not found!".format(char_specifier))

        read_result = await wrap_IAsyncOperation(
            IAsyncOperation[GattReadResult](
                characteristic.obj.ReadValueAsync(
                    BluetoothCacheMode.Cached
                    if use_cached
                    else BluetoothCacheMode.Uncached
                )
            ),
            return_type=GattReadResult,
        )
        if read_result.Status == GattCommunicationStatus.Success:
            with BleakDataReader(read_result.Value) as reader:
                value = bytearray(reader.read())
            logger.debug(
                "Read Characteristic {0} : {1}".format(characteristic.uuid, value)
            )
        else:
            if read_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakDotNetTaskError(
                    "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                        characteristic.uuid,
                        _communication_statues.get(read_result.Status, ""),
                        read_result.ProtocolError,
                        CONTROLLER_ERROR_CODES.get(
                            read_result.ProtocolError, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not read characteristic value for {0}: {1}".format(
                        characteristic.uuid,
                        _communication_statues.get(read_result.Status, ""),
                    )
                )
        return value

    async def read_gatt_descriptor(
        self, handle: int, use_cached=False, **kwargs
    ) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            use_cached (bool): `False` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.

        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))

        read_result = await wrap_IAsyncOperation(
            IAsyncOperation[GattReadResult](
                descriptor.obj.ReadValueAsync(
                    BluetoothCacheMode.Cached
                    if use_cached
                    else BluetoothCacheMode.Uncached
                )
            ),
            return_type=GattReadResult,
        )
        if read_result.Status == GattCommunicationStatus.Success:
            with BleakDataReader(read_result.Value) as reader:
                value = bytearray(reader.read())
            logger.debug("Read Descriptor {0} : {1}".format(handle, value))
        else:
            if read_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakDotNetTaskError(
                    "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X}: {3})".format(
                        descriptor.uuid,
                        _communication_statues.get(read_result.Status, ""),
                        read_result.ProtocolError,
                        CONTROLLER_ERROR_CODES.get(
                            read_result.ProtocolError, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not read Descriptor value for {0}: {1}".format(
                        descriptor.uuid,
                        _communication_statues.get(read_result.Status, ""),
                    )
                )

        return value

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: bytearray,
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

        with BleakDataWriter(data) as writer:
            response = (
                GattWriteOption.WriteWithResponse
                if response
                else GattWriteOption.WriteWithoutResponse
            )
            write_result = await wrap_IAsyncOperation(
                IAsyncOperation[GattWriteResult](
                    characteristic.obj.WriteValueWithResultAsync(
                        writer.detach_buffer(), response
                    )
                ),
                return_type=GattWriteResult,
            )

        if write_result.Status == GattCommunicationStatus.Success:
            logger.debug(
                "Write Characteristic {0} : {1}".format(characteristic.uuid, data)
            )
        else:
            if write_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2} (Error: 0x{3:02X}: {4})".format(
                        data,
                        characteristic.uuid,
                        _communication_statues.get(write_result.Status, ""),
                        write_result.ProtocolError,
                        CONTROLLER_ERROR_CODES.get(
                            write_result.ProtocolError, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2}".format(
                        data,
                        characteristic.uuid,
                        _communication_statues.get(write_result.Status, ""),
                    )
                )

    async def write_gatt_descriptor(self, handle: int, data: bytearray) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            data (bytes or bytearray): The data to send.

        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))

        with BleakDataWriter(data) as writer:
            write_result = await wrap_IAsyncOperation(
                IAsyncOperation[GattWriteResult](
                    descriptor.obj.WriteValueAsync(writer.DetachBuffer())
                ),
                return_type=GattWriteResult,
            )

        if write_result.Status == GattCommunicationStatus.Success:
            logger.debug("Write Descriptor {0} : {1}".format(handle, data))
        else:
            if write_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2} (Error: 0x{3:02X}: {4})".format(
                        data,
                        descriptor.uuid,
                        _communication_statues.get(write_result.Status, ""),
                        write_result.ProtocolError,
                        CONTROLLER_ERROR_CODES.get(
                            write_result.ProtocolError, "Unknown"
                        ),
                    )
                )
            else:
                raise BleakError(
                    "Could not write value {0} to descriptor {1}: {2}".format(
                        data,
                        descriptor.uuid,
                        _communication_statues.get(write_result.Status, ""),
                    )
                )

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs
    ) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be a integer handle of the characteristic generating the
        data and the second will be a ``bytearray`` containing the data sent from the connected server.

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
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {0} not found!".format(char_specifier))

        if self._notification_callbacks.get(characteristic.handle):
            await self.stop_notify(characteristic)

        status = await self._start_notify(characteristic, callback)

        if status != GattCommunicationStatus.Success:
            # TODO: Find out how to get the ProtocolError code that describes a potential GattCommunicationStatus.ProtocolError result.
            raise BleakError(
                "Could not start notify on {0}: {1}".format(
                    characteristic.uuid, _communication_statues.get(status, "")
                )
            )

    async def _start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: Callable[[str, Any], Any],
    ):
        """Internal method performing call to BleakUWPBridge method.

        Args:
            characteristic: The BleakGATTCharacteristic to start notification on.
            callback: The function to be called on notification.

        Returns:
            (int) The GattCommunicationStatus of the operation.

        """
        characteristic_obj = characteristic.obj
        if (
            characteristic_obj.CharacteristicProperties
            & GattCharacteristicProperties.Indicate
        ):
            cccd = GattClientCharacteristicConfigurationDescriptorValue.Indicate
        elif (
            characteristic_obj.CharacteristicProperties
            & GattCharacteristicProperties.Notify
        ):
            cccd = GattClientCharacteristicConfigurationDescriptorValue.Notify
        else:
            cccd = getattr(GattClientCharacteristicConfigurationDescriptorValue, "None")

        try:
            # TODO: Enable adding multiple handlers!
            self._notification_callbacks[characteristic.handle] = TypedEventHandler[
                GattCharacteristic, GattValueChangedEventArgs
            ](_notification_wrapper(callback, asyncio.get_event_loop()))
            self._bridge.AddValueChangedCallback(
                characteristic_obj, self._notification_callbacks[characteristic.handle]
            )
        except Exception as e:
            logger.debug("Start Notify problem: {0}".format(e))
            if characteristic_obj.Uuid.ToString() in self._notification_callbacks:
                callback = self._notification_callbacks.pop(characteristic.handle)
                self._bridge.RemoveValueChangedCallback(characteristic_obj)
                del callback

            return GattCommunicationStatus.AccessDenied

        status = await wrap_IAsyncOperation(
            IAsyncOperation[GattCommunicationStatus](
                characteristic_obj.WriteClientCharacteristicConfigurationDescriptorAsync(
                    cccd
                )
            ),
            return_type=GattCommunicationStatus,
        )

        if status != GattCommunicationStatus.Success:
            # This usually happens when a device reports that it support indicate,
            # but it actually doesn't.
            if characteristic.handle in self._notification_callbacks:
                callback = self._notification_callbacks.pop(characteristic.handle)
                self._bridge.RemoveValueChangedCallback(characteristic_obj)
                del callback

            return GattCommunicationStatus.AccessDenied
        return status

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

        status = await wrap_IAsyncOperation(
            IAsyncOperation[GattCommunicationStatus](
                characteristic.obj.WriteClientCharacteristicConfigurationDescriptorAsync(
                    getattr(
                        GattClientCharacteristicConfigurationDescriptorValue, "None"
                    )
                )
            ),
            return_type=GattCommunicationStatus,
        )

        if status != GattCommunicationStatus.Success:
            raise BleakError(
                "Could not stop notify on {0}: {1}".format(
                    characteristic.uuid, _communication_statues.get(status, "")
                )
            )
        else:
            callback = self._notification_callbacks.pop(characteristic.handle)
            self._bridge.RemoveValueChangedCallback(characteristic.obj)
            del callback


def _notification_wrapper(func: Callable, loop: asyncio.AbstractEventLoop):
    @wraps(func)
    def dotnet_notification_parser(sender: Any, args: Any):
        # Return only the UUID string representation as sender.
        # Also do a conversion from System.Bytes[] to bytearray.
        with BleakDataReader(args.CharacteristicValue) as reader:
            output = reader.read()

        return loop.call_soon_threadsafe(
            func, sender.AttributeHandle, bytearray(output)
        )

    return dotnet_notification_parser
