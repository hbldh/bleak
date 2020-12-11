"""
BLE Client for CoreBluetooth on macOS

Created on 2019-06-26 by kevincar <kevincarrolldavis@gmail.com>
"""

import logging
import uuid
from typing import Callable, Union
import asyncio

from Foundation import NSData
from CoreBluetooth import (
    CBCharacteristicWriteWithResponse,
    CBCharacteristicWriteWithoutResponse,
)

from bleak.backends.client import BaseBleakClient
from bleak.backends.corebluetooth.characteristic import (
    BleakGATTCharacteristicCoreBluetooth,
)
from bleak.backends.corebluetooth.descriptor import BleakGATTDescriptorCoreBluetooth
from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth
from bleak.backends.corebluetooth.service import BleakGATTServiceCoreBluetooth
from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.characteristic import BleakGATTCharacteristic

from bleak.exc import BleakError

logger = logging.getLogger(__name__)


class BleakClientCoreBluetooth(BaseBleakClient):
    """CoreBluetooth class interface for BleakClient

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
        timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super(BleakClientCoreBluetooth, self).__init__(address_or_ble_device, **kwargs)

        if isinstance(address_or_ble_device, BLEDevice):
            self._device_info = address_or_ble_device.details
            self._central_manager_delegate = address_or_ble_device.metadata["delegate"]
        else:
            self._device_info = None
            self._central_manager_delegate = None
        self._requester = None
        self._callbacks = {}
        self._services = None

    def __str__(self):
        return "BleakClientCoreBluetooth ({})".format(self.address)

    async def connect(self, **kwargs) -> bool:
        """Connect to a specified Peripheral

        Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

        Returns:
            Boolean representing connection status.

        """
        timeout = kwargs.get("timeout", self._timeout)
        if self._device_info is None:
            device = await BleakScannerCoreBluetooth.find_device_by_address(
                self.address, timeout=timeout
            )

            if device:
                self._device_info = device.details
                self._central_manager_delegate = device.metadata["delegate"]
            else:
                raise BleakError(
                    "Device with address {} was not found".format(self.address)
                )
        # self._device_info.manager() should return a CBCentralManager

        manager = self._central_manager_delegate
        logger.debug("CentralManagerDelegate  at {}".format(manager))
        logger.debug("Connecting to BLE device @ {}".format(self.address))
        await manager.connect_(self._device_info, timeout=timeout)
        manager.disconnected_callback = self._disconnected_callback_client

        # Now get services
        await self.get_services()

        return True

    def _disconnected_callback_client(self):
        """
        Callback for device disconnection. Bleak callback sends one argument as client. This is wrapper function
        that gets called from the CentralManager and call actual disconnected_callback by sending client as argument
        """
        logger.debug("Received disconnection callback...")

        if self._disconnected_callback is not None:
            self._disconnected_callback(self)

    async def disconnect(self) -> bool:
        """Disconnect from the peripheral device"""
        manager = self._central_manager_delegate
        if manager is None:
            return False
        await manager.disconnect()
        self.services = BleakGATTServiceCollection()
        # Ensure that `get_services` retrieves services again, rather than using the cached object
        self._services_resolved = False
        self._services = None
        return True

    async def is_connected(self) -> bool:
        """Checks for current active connection"""
        manager = self._central_manager_delegate
        return False if manager is None else manager.isConnected

    async def pair(self, *args, **kwargs) -> bool:
        """Attempt to pair with a peripheral.

        .. note::

            This is not available on macOS since there is not explicit method to do a pairing, Instead the docs
            state that it "auto-pairs" when trying to read a characteristic that requires encryption, something
            Bleak cannot do apparently.

        Reference:

            - `Apple Docs <https://developer.apple.com/library/archive/documentation/NetworkingInternetWeb/Conceptual/CoreBluetooth_concepts/BestPracticesForSettingUpYourIOSDeviceAsAPeripheral/BestPracticesForSettingUpYourIOSDeviceAsAPeripheral.html#//apple_ref/doc/uid/TP40013257-CH5-SW1>`_
            - `Stack Overflow post #1 <https://stackoverflow.com/questions/25254932/can-you-pair-a-bluetooth-le-device-in-an-ios-app>`_
            - `Stack Overflow post #2 <https://stackoverflow.com/questions/47546690/ios-bluetooth-pairing-request-dialog-can-i-know-the-users-choice>`_

        Returns:
            Boolean regarding success of pairing.

        """
        raise NotImplementedError("Pairing is not available in Core Bluetooth.")

    async def unpair(self) -> bool:
        """

        Returns:

        """
        raise NotImplementedError("Pairing is not available in Core Bluetooth.")

    async def get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self._services is not None:
            return self.services

        logger.debug("Retrieving services...")
        manager = self._central_manager_delegate
        services = await manager.connected_peripheral_delegate.discoverServices()

        for service in services:
            serviceUUID = service.UUID().UUIDString()
            logger.debug(
                "Retrieving characteristics for service {}".format(serviceUUID)
            )
            characteristics = (
                await manager.connected_peripheral_delegate.discoverCharacteristics_(
                    service
                )
            )

            self.services.add_service(BleakGATTServiceCoreBluetooth(service))

            for characteristic in characteristics:
                cUUID = characteristic.UUID().UUIDString()
                logger.debug(
                    "Retrieving descriptors for characteristic {}".format(cUUID)
                )
                descriptors = (
                    await manager.connected_peripheral_delegate.discoverDescriptors_(
                        characteristic
                    )
                )

                self.services.add_characteristic(
                    BleakGATTCharacteristicCoreBluetooth(characteristic)
                )
                for descriptor in descriptors:
                    self.services.add_descriptor(
                        BleakGATTDescriptorCoreBluetooth(
                            descriptor,
                            cb_uuid_to_str(characteristic.UUID()),
                            int(characteristic.handle()),
                        )
                    )
        logger.debug("Services resolved for %s", str(self))
        self._services_resolved = True
        self._services = services
        return self.services

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
            use_cached (bool): `False` forces macOS to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.

        """
        manager = self._central_manager_delegate

        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))

        output = await manager.connected_peripheral_delegate.readCharacteristic_(
            characteristic.obj, use_cached=use_cached
        )
        value = bytearray(output)
        logger.debug("Read Characteristic {0} : {1}".format(characteristic.uuid, value))
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
        manager = self._central_manager_delegate

        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor {} was not found!".format(handle))

        output = await manager.connected_peripheral_delegate.readDescriptor_(
            descriptor.obj, use_cached=use_cached
        )
        if isinstance(
            output, str
        ):  # Sometimes a `pyobjc_unicode`or `__NSCFString` is returned and they can be used as regular Python strings.
            value = bytearray(output.encode("utf-8"))
        else:  # _NSInlineData
            value = bytearray(output)  # value.getBytes_length_(None, len(value))
        logger.debug("Read Descriptor {0} : {1}".format(handle, value))
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
        manager = self._central_manager_delegate

        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))

        value = NSData.alloc().initWithBytes_length_(data, len(data))
        success = (
            await manager.connected_peripheral_delegate.writeCharacteristic_value_type_(
                characteristic.obj,
                value,
                CBCharacteristicWriteWithResponse
                if response
                else CBCharacteristicWriteWithoutResponse,
            )
        )
        if success:
            logger.debug(
                "Write Characteristic {0} : {1}".format(characteristic.uuid, data)
            )
        else:
            raise BleakError(
                "Could not write value {0} to characteristic {1}: {2}".format(
                    data, characteristic.uuid, success
                )
            )

    async def write_gatt_descriptor(self, handle: int, data: bytearray) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            data (bytes or bytearray): The data to send.

        """
        manager = self._central_manager_delegate

        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor {} was not found!".format(handle))

        value = NSData.alloc().initWithBytes_length_(data, len(data))
        success = await manager.connected_peripheral_delegate.writeDescriptor_value_(
            descriptor.obj, value
        )
        if success:
            logger.debug("Write Descriptor {0} : {1}".format(handle, data))
        else:
            raise BleakError(
                "Could not write value {0} to descriptor {1}: {2}".format(
                    data, descriptor.uuid, success
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
        manager = self._central_manager_delegate

        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {0} not found!".format(char_specifier))

        success = await manager.connected_peripheral_delegate.startNotify_cb_(
            characteristic.obj, callback
        )
        if not success:
            raise BleakError(
                "Could not start notify on {0}: {1}".format(
                    characteristic.uuid, success
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
        manager = self._central_manager_delegate

        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} not found!".format(char_specifier))

        success = await manager.connected_peripheral_delegate.stopNotify_(
            characteristic.obj
        )
        if not success:
            raise BleakError(
                "Could not stop notify on {0}: {1}".format(characteristic.uuid, success)
            )

    async def get_rssi(self) -> int:
        """To get RSSI value in dBm of the connected Peripheral"""

        self._device_info.readRSSI()
        manager = self._central_manager_delegate
        RSSI = manager.connected_peripheral.RSSI()
        for i in range(20):  # First time takes a little otherwise returns None
            RSSI = manager.connected_peripheral.RSSI()
            if not RSSI:
                await asyncio.sleep(0.1)
            else:
                return int(RSSI)

        if not RSSI:
            return None
