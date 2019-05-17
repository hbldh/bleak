# -*- coding: utf-8 -*-
"""
BLE Client for Windows 10 systems.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>
"""

import logging
import asyncio
from asyncio.events import AbstractEventLoop
from functools import wraps
from typing import Callable, Any

from bleak.exc import BleakError, BleakDotNetTaskError
from bleak.backends.client import BaseBleakClient
from bleak.backends.dotnet.discovery import discover
from bleak.backends.dotnet.utils import (
    wrap_Task,
    wrap_IAsyncOperation,
    IAsyncOperationAwaitable,
)
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


class BleakClientDotNet(BaseBleakClient):
    """The native Windows Bleak Client.

    Implemented using `pythonnet <https://pythonnet.github.io/>`_, a package that provides an integration to the .NET
    Common Language Runtime (CLR). Therefore, much of the code below has a distinct C# feel.
    """

    def __init__(self, address: str, loop: AbstractEventLoop = None, **kwargs):
        super(BleakClientDotNet, self).__init__(address, loop, **kwargs)

        # Backend specific. Python.NET objects.
        self._device_info = None
        self._requester = None
        self._bridge = Bridge()
        self._callbacks = {}

    def __str__(self):
        return "BleakClientDotNet ({0})".format(self.address)

    # Connectivity methods

    async def connect(self) -> bool:
        """Connect to the specified GATT server.

        Returns:
            Boolean representing connection status.

        """
        # Try to find the desired device.
        devices = await discover(2.0, loop=self.loop)
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

        self._requester = await wrap_IAsyncOperation(
            IAsyncOperation[BluetoothLEDevice](
                BluetoothLEDevice.FromBluetoothAddressAsync(
                    UInt64(self._device_info.BluetoothAddress)
                )
            ),
            return_type=BluetoothLEDevice,
            loop=self.loop,
        )

        def _ConnectionStatusChanged_Handler(sender, args):
            logger.debug("_ConnectionStatusChanged_Handler: " + args.ToString())

        self._requester.ConnectionStatusChanged += _ConnectionStatusChanged_Handler

        # Obtain services, which also leads to connection being established.
        await self.get_services()
        await asyncio.sleep(0.2, loop=self.loop)
        connected = await self.is_connected()
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
                raise BleakDotNetTaskError("Could not get GATT services.")

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
                    raise BleakDotNetTaskError(
                        "Could not get GATT characteristics for {0}.".format(service)
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
                        raise BleakDotNetTaskError(
                            "Could not get GATT descriptors for {0}.".format(
                                characteristic
                            )
                        )
                    for descriptor in list(descriptors_result.Descriptors):
                        self.services.add_descriptor(
                            BleakGATTDescriptorDotNet(
                                descriptor, characteristic.Uuid.ToString()
                            )
                        )

            self._services_resolved = True
            return self.services

    # I/O methods

    async def read_gatt_char(self, _uuid: str, use_cached=False, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to read from.
            use_cached (bool): `False` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.

        """
        characteristic = self.services.get_characteristic(str(_uuid))
        if not characteristic:
            raise BleakError("Characteristic {0} was not found!".format(_uuid))

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
            logger.debug("Read Characteristic {0} : {1}".format(_uuid, value))
        else:
            raise BleakError(
                "Could not read characteristic value for {0}: {1}".format(
                    characteristic.uuid, read_result.Status
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
            raise BleakError(
                "Could not read Descriptor value for {0}: {1}".format(
                    descriptor.uuid, read_result.Status
                )
            )

        return value

    async def write_gatt_char(
        self, _uuid: str, data: bytearray, response: bool = False
    ) -> None:
        """Perform a write operation of the specified GATT characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to write to.
            data (bytes or bytearray): The data to send.
            response (bool): If write-with-response operation should be done. Defaults to `False`.

        """
        characteristic = self.services.get_characteristic(str(_uuid))
        if not characteristic:
            raise BleakError("Characteristic {0} was not found!".format(_uuid))

        writer = DataWriter()
        writer.WriteBytes(Array[Byte](data))
        response = GattWriteOption.WriteWithResponse if response else GattWriteOption.WriteWithoutResponse
        write_result = await wrap_IAsyncOperation(
            IAsyncOperation[GattWriteResult](
                characteristic.obj.WriteValueWithResultAsync(writer.DetachBuffer(), response)
            ),
            return_type=GattWriteResult,
            loop=self.loop,
        )
        if write_result.Status == GattCommunicationStatus.Success:
            logger.debug("Write Characteristic {0} : {1}".format(_uuid, data))
        else:
            raise BleakError(
                "Could not write value {0} to characteristic {1}: {2}".format(
                    data, characteristic.uuid, write_result.Status
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
            raise BleakError("Descriptor {0} was not found!".format(handle))

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
            raise BleakError(
                "Could not write value {0} to descriptor {1}: {2}".format(
                    data, descriptor.uuid, write_result.Status
                )
            )

    async def start_notify(
        self, _uuid: str, callback: Callable[[str, Any], Any], **kwargs
    ) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be a uuid string
        object and the second will be a bytearray.

        .. code-block:: python

            def callback(sender, data):
                print(f"{sender}: {data}")
            client.start_notify(char_uuid, callback)

        Args:
            _uuid (str or UUID): The uuid of the characteristics to start notification/indication on.
            callback (function): The function to be called on notification.

        """
        characteristic = self.services.get_characteristic(str(_uuid))

        if self._notification_callbacks.get(str(_uuid)):
            await self.stop_notify(_uuid)

        status = await self._start_notify(characteristic.obj, callback)

        if status != GattCommunicationStatus.Success:
            raise BleakError(
                "Could not start notify on {0}: {1}".format(characteristic.uuid, status)
            )

    async def _start_notify(
        self,
        characteristic_obj: GattCharacteristic,
        callback: Callable[[str, Any], Any],
    ):
        """Internal method performing call to BleakUWPBridge method.

        Args:
            characteristic_obj: The Managed Windows.Devices.Bluetooth.GenericAttributeProfile.GattCharacteristic Object
            callback: The function to be called on notification.

        Returns:
            (int) The GattCommunicationStatus of the operation.

        """

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
            self._callbacks[characteristic_obj.Uuid.ToString()] = TypedEventHandler[
                GattCharacteristic, GattValueChangedEventArgs
            ](_notification_wrapper(callback))
            self._bridge.AddValueChangedCallback(
                characteristic_obj, self._callbacks[characteristic_obj.Uuid.ToString()]
            )
        except Exception as e:
            logger.debug("Start Notify problem: {0}".format(e))
            if characteristic_obj.Uuid.ToString() in self._callbacks:
                callback = self._callbacks.pop(characteristic_obj.Uuid.ToString())
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
            # This usually happens when a device reports that it support indicate, but it actually doesn't.
            if characteristic_obj.Uuid.ToString() in self._callbacks:
                callback = self._callbacks.pop(characteristic_obj.Uuid.ToString())
                self._bridge.RemoveValueChangedCallback(characteristic_obj, callback)

            return GattCommunicationStatus.AccessDenied
        return status

    async def stop_notify(self, _uuid: str) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            _uuid: The characteristic to stop notifying/indicating on.

        """
        characteristic = self.services.get_characteristic(str(_uuid))

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
                "Could not start notify on {0}: {1}".format(characteristic.uuid, status)
            )
        else:
            callback = self._callbacks.pop(characteristic.uuid)
            self._bridge.RemoveValueChangedCallback(characteristic.obj, callback)


def _notification_wrapper(func: Callable):
    @wraps(func)
    def dotnet_notification_parser(sender: Any, args: Any):
        # Return only the UUID string representation as sender.
        # Also do a conversion from System.Bytes[] to bytearray.
        reader = DataReader.FromBuffer(args.CharacteristicValue)
        output = Array.CreateInstance(Byte, reader.UnconsumedBufferLength)
        reader.ReadBytes(output)

        return func(sender.Uuid.ToString(), bytearray(output))

    return dotnet_notification_parser
