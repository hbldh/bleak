# -*- coding: utf-8 -*-
"""
BLE Client for Windows 10 systems.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>
"""

import logging
import asyncio
import uuid
from asyncio.events import AbstractEventLoop
from functools import wraps
from typing import Callable, Any, Union

from bleak.exc import BleakError, BleakDotNetTaskError
from bleak.backends.client import BaseBleakClient
from bleak.backends.dotnet.discovery import discover
from bleak.backends.dotnet.utils import (
    wrap_Task,
    wrap_IAsyncOperation,
    IAsyncOperationAwaitable,
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
from System import Array, Byte, UInt64
from Windows.Foundation import IAsyncOperation, TypedEventHandler
from Windows.Storage.Streams import DataReader, DataWriter, IBuffer
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


class BleakClientDotNet(BaseBleakClient):
    """The native Windows Bleak Client.

    Implemented using `pythonnet <https://pythonnet.github.io/>`_, a package that provides an integration to the .NET
    Common Language Runtime (CLR). Therefore, much of the code below has a distinct C# feel.

    Args:
        address (str): The MAC address of the BLE peripheral to connect to.
        loop (asyncio.events.AbstractEventLoop): The event loop to use.

    Keyword Args:
            timeout (float): Timeout for required ``discover`` call. Defaults to 2.0.

    """

    def __init__(self, address: str, loop: AbstractEventLoop = None, **kwargs):
        super(BleakClientDotNet, self).__init__(address, loop, **kwargs)

        # Backend specific. Python.NET objects.
        self._device_info = None
        self._requester = None
        self._bridge = Bridge()

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
            timeout (float): Timeout for required ``discover`` call. Defaults to 2.0.

        Returns:
            Boolean representing connection status.

        """
        # Try to find the desired device.
        timeout = kwargs.get("timeout", self._timeout)
        devices = await discover(timeout=timeout, loop=self.loop)
        sought_device = list(
            filter(lambda x: x.address.upper() == self.address.upper(), devices)
        )

        if len(sought_device):
            self._device_info = sought_device[0].details
        else:
            raise BleakError(
                "Device with address {0} was " "not found.".format(self.address)
            )

        logger.debug("Connecting to BLE device @ {0}".format(self.address))

        args = [UInt64(self._device_info.BluetoothAddress)]
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
            loop=self.loop,
        )

        def _ConnectionStatusChanged_Handler(sender, args):
            logger.debug("_ConnectionStatusChanged_Handler: " + args.ToString())

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
                await asyncio.sleep(0.2, loop=self.loop)
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
            Boolean representing connection status.

        """
        logger.debug("Disconnecting from BLE device...")
        # Remove notifications
        # TODO: Make sure all notifications are removed prior to Dispose.
        # Dispose all components that we have requested and created.
        for service in self.services:
            service.obj.Dispose()
        self.services = BleakGATTServiceCollection()
        self._requester.Dispose()
        self._requester = None

        return not await self.is_connected()

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

    def set_disconnected_callback(
        self, callback: Callable[[BaseBleakClient], None], **kwargs
    ) -> None:
        """Set the disconnected callback.

        N.B. This is not implemented in the .NET backend yet.

        Args:
            callback: callback to be called on disconnection.

        """
        raise NotImplementedError("This is not implemented in the .NET backend yet")

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
                loop=self.loop,
            )

            if services_result.Status != GattCommunicationStatus.Success:
                if services_result.Status == GattCommunicationStatus.ProtocolError:
                    raise BleakDotNetTaskError(
                        "Could not get GATT services: {0} (Error: 0x{1:02X})".format(
                            _communication_statues.get(services_result.Status, ""),
                            services_result.ProtocolError,
                        )
                    )
                else:
                    raise BleakDotNetTaskError(
                        "Could not get GATT services: {0}".format(
                            _communication_statues.get(services_result.Status, "")
                        )
                    )

            # TODO: Check if fetching yeilds failures...
            for service in services_result.Services:
                characteristics_result = await wrap_IAsyncOperation(
                    IAsyncOperation[GattCharacteristicsResult](
                        service.GetCharacteristicsAsync()
                    ),
                    return_type=GattCharacteristicsResult,
                    loop=self.loop,
                )
                self.services.add_service(BleakGATTServiceDotNet(service))
                if characteristics_result.Status != GattCommunicationStatus.Success:
                    if (
                        characteristics_result.Status
                        == GattCommunicationStatus.ProtocolError
                    ):
                        raise BleakDotNetTaskError(
                            "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X})".format(
                                service,
                                _communication_statues.get(
                                    characteristics_result.Status, ""
                                ),
                                characteristics_result.ProtocolError,
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
                        loop=self.loop,
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
                                "Could not get GATT descriptors for {0}: {1} (Error: 0x{2:02X})".format(
                                    service,
                                    _communication_statues.get(
                                        descriptors_result.Status, ""
                                    ),
                                    descriptors_result.ProtocolError,
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
            loop=self.loop,
        )
        if read_result.Status == GattCommunicationStatus.Success:
            reader = DataReader.FromBuffer(IBuffer(read_result.Value))
            output = Array.CreateInstance(Byte, reader.UnconsumedBufferLength)
            reader.ReadBytes(output)
            value = bytearray(output)
            logger.debug(
                "Read Characteristic {0} : {1}".format(characteristic.uuid, value)
            )
        else:
            if read_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakDotNetTaskError(
                    "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X})".format(
                        characteristic.uuid,
                        _communication_statues.get(read_result.Status, ""),
                        read_result.ProtocolError,
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
            loop=self.loop,
        )
        if read_result.Status == GattCommunicationStatus.Success:
            reader = DataReader.FromBuffer(IBuffer(read_result.Value))
            output = Array.CreateInstance(Byte, reader.UnconsumedBufferLength)
            reader.ReadBytes(output)
            value = bytearray(output)
            logger.debug("Read Descriptor {0} : {1}".format(handle, value))
        else:
            if read_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakDotNetTaskError(
                    "Could not get GATT characteristics for {0}: {1} (Error: 0x{2:02X})".format(
                        descriptor.uuid,
                        _communication_statues.get(read_result.Status, ""),
                        read_result.ProtocolError,
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

        writer = DataWriter()
        writer.WriteBytes(Array[Byte](data))
        response = (
            GattWriteOption.WriteWithResponse
            if response
            else GattWriteOption.WriteWithoutResponse
        )
        write_result = await wrap_IAsyncOperation(
            IAsyncOperation[GattWriteResult](
                characteristic.obj.WriteValueWithResultAsync(
                    writer.DetachBuffer(), response
                )
            ),
            return_type=GattWriteResult,
            loop=self.loop,
        )
        if write_result.Status == GattCommunicationStatus.Success:
            logger.debug(
                "Write Characteristic {0} : {1}".format(characteristic.uuid, data)
            )
        else:
            if write_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2} (Error: 0x{3:02X})".format(
                        data,
                        characteristic.uuid,
                        _communication_statues.get(write_result.Status, ""),
                        write_result.ProtocolError,
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

        writer = DataWriter()
        writer.WriteBytes(Array[Byte](data))
        write_result = await wrap_IAsyncOperation(
            IAsyncOperation[GattWriteResult](
                descriptor.obj.WriteValueAsync(writer.DetachBuffer())
            ),
            return_type=GattWriteResult,
            loop=self.loop,
        )
        if write_result.Status == GattCommunicationStatus.Success:
            logger.debug("Write Descriptor {0} : {1}".format(handle, data))
        else:
            if write_result.Status == GattCommunicationStatus.ProtocolError:
                raise BleakError(
                    "Could not write value {0} to characteristic {1}: {2} (Error: 0x{3:02X})".format(
                        data,
                        descriptor.uuid,
                        _communication_statues.get(write_result.Status, ""),
                        write_result.ProtocolError,
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
        callback: Callable[[str, Any], Any],
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
            # TODO: Find out how to get the ProtocolError code that describes a
            #  potential GattCommunicationStatus.ProtocolError result.
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
            ](_notification_wrapper(self.loop, callback))
            self._bridge.AddValueChangedCallback(
                characteristic_obj, self._notification_callbacks[characteristic.handle]
            )
        except Exception as e:
            logger.debug("Start Notify problem: {0}".format(e))
            if characteristic_obj.Uuid.ToString() in self._notification_callbacks:
                callback = self._notification_callbacks.pop(characteristic.handle)
                self._bridge.RemoveValueChangedCallback(characteristic_obj, callback)

            return GattCommunicationStatus.AccessDenied

        status = await wrap_IAsyncOperation(
            IAsyncOperation[GattCommunicationStatus](
                characteristic_obj.WriteClientCharacteristicConfigurationDescriptorAsync(
                    cccd
                )
            ),
            return_type=GattCommunicationStatus,
            loop=self.loop,
        )

        if status != GattCommunicationStatus.Success:
            # This usually happens when a device reports that it support indicate,
            # but it actually doesn't.
            if characteristic.handle in self._notification_callbacks:
                callback = self._notification_callbacks.pop(characteristic.handle)
                self._bridge.RemoveValueChangedCallback(characteristic_obj, callback)

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
            loop=self.loop,
        )

        if status != GattCommunicationStatus.Success:
            raise BleakError(
                "Could not stop notify on {0}: {1}".format(
                    characteristic.uuid, _communication_statues.get(status, "")
                )
            )
        else:
            callback = self._notification_callbacks.pop(characteristic.handle)
            self._bridge.RemoveValueChangedCallback(characteristic.obj, callback)


def _notification_wrapper(loop: AbstractEventLoop, func: Callable):
    @wraps(func)
    def dotnet_notification_parser(sender: Any, args: Any):
        # Return only the UUID string representation as sender.
        # Also do a conversion from System.Bytes[] to bytearray.
        reader = DataReader.FromBuffer(args.CharacteristicValue)
        output = Array.CreateInstance(Byte, reader.UnconsumedBufferLength)
        reader.ReadBytes(output)

        return loop.call_soon_threadsafe(
            func, sender.Uuid.ToString(), bytearray(output)
        )

    return dotnet_notification_parser
