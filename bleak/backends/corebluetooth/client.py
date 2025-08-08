# Created on 2019-06-26 by kevincar <kevincarrolldavis@gmail.com>
"""
BLE Client for CoreBluetooth on macOS
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import asyncio
import logging
from typing import Any, Optional, Union

if sys.version_info < (3, 12):
    from typing_extensions import Buffer, override
else:
    from collections.abc import Buffer
    from typing import override

from CoreBluetooth import (
    CBUUID,
    CBCharacteristicWriteWithoutResponse,
    CBCharacteristicWriteWithResponse,
    CBPeripheral,
    CBPeripheralStateConnected,
)
from Foundation import NSArray, NSData

from bleak import BleakScanner
from bleak.args.corebluetooth import CBStartNotifyArgs
from bleak.assigned_numbers import gatt_char_props_to_strs
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient, NotifyCallback
from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.corebluetooth.PeripheralDelegate import PeripheralDelegate
from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth
from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection
from bleak.exc import BleakDeviceNotFoundError, BleakError

logger = logging.getLogger(__name__)


class BleakClientCoreBluetooth(BaseBleakClient):
    """CoreBluetooth class interface for BleakClient

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.
        services: Optional set of service UUIDs that will be used.

    Keyword Args:
        timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

    """

    def __init__(
        self,
        address_or_ble_device: Union[BLEDevice, str],
        services: Optional[set[str]] = None,
        **kwargs: Any,
    ):
        super(BleakClientCoreBluetooth, self).__init__(address_or_ble_device, **kwargs)

        self._peripheral: Optional[CBPeripheral] = None
        self._delegate: Optional[PeripheralDelegate] = None
        self._central_manager_delegate: Optional[CentralManagerDelegate] = None

        if isinstance(address_or_ble_device, BLEDevice):
            (
                self._peripheral,
                self._central_manager_delegate,
            ) = address_or_ble_device.details

        self._requested_services = (
            NSArray[CBUUID]
            .alloc()
            .initWithArray_(list(map(CBUUID.UUIDWithString_, services)))
            if services
            else None
        )

    def __str__(self) -> str:
        return "BleakClientCoreBluetooth ({})".format(self.address)

    @override
    async def connect(self, pair: bool, **kwargs: Any) -> None:
        """Connect to a specified Peripheral

        Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.
        """
        if pair:
            logger.debug("Explicit pairing is not available in CoreBluetooth.")

        timeout = kwargs.get("timeout", self._timeout)
        if self._peripheral is None:
            device = await BleakScanner.find_device_by_address(
                self.address, timeout=timeout, backend=BleakScannerCoreBluetooth
            )

            if device:
                self._peripheral, self._central_manager_delegate = device.details
            else:
                raise BleakDeviceNotFoundError(
                    self.address, f"Device with address {self.address} was not found"
                )

        if self._delegate is None:
            self._delegate = PeripheralDelegate.alloc().initWithPeripheral_(
                self._peripheral
            )

        def disconnect_callback() -> None:
            # Ensure that `get_services` retrieves services again, rather
            # than using the cached object
            self.services = None

            # If there are any pending futures waiting for delegate callbacks, we
            # need to raise an exception since the callback will no longer be
            # called because the device is disconnected.
            for future in self._delegate.futures():
                try:
                    future.set_exception(BleakError("disconnected"))
                except asyncio.InvalidStateError:
                    # the future was already done
                    pass

            if self._disconnected_callback:
                self._disconnected_callback()

        manager = self._central_manager_delegate
        logger.debug("CentralManagerDelegate  at {}".format(manager))
        logger.debug("Connecting to BLE device @ {}".format(self.address))
        await manager.connect(self._peripheral, disconnect_callback, timeout=timeout)

        # Now get services
        await self._get_services()

    @override
    async def disconnect(self) -> None:
        """Disconnect from the peripheral device"""
        if (
            self._peripheral is None
            or self._peripheral.state() != CBPeripheralStateConnected
        ):
            return

        assert self._central_manager_delegate
        await self._central_manager_delegate.disconnect(self._peripheral)

    @property
    @override
    def is_connected(self) -> bool:
        """Checks for current active connection"""
        return (
            False
            if self._peripheral is None
            else self._peripheral.state() == CBPeripheralStateConnected
        )

    @property
    @override
    def name(self) -> str:
        """Get the name of the connected peripheral"""
        if self._peripheral is None:
            raise BleakError("Not connected")
        return self._peripheral.name()

    @property
    @override
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        # Use type CBCharacteristicWriteWithoutResponse to get maximum write
        # value length based on the negotiated ATT MTU size. Add the ATT header
        # length (+3) to get the actual ATT MTU size.
        assert self._peripheral
        return (
            self._peripheral.maximumWriteValueLengthForType_(
                CBCharacteristicWriteWithoutResponse
            )
            + 3
        )

    @override
    async def pair(self, *args: Any, **kwargs: Any) -> None:
        """Attempt to pair with a peripheral.

        Raises:
            NotImplementedError:
                This is not available on macOS since there is not explicit API
                to do a pairing. Instead, the docs state that it "auto-pairs",
                when trying to read a characteristic that requires encryption.

        Reference:

            - `Apple Docs <https://developer.apple.com/library/archive/documentation/NetworkingInternetWeb/Conceptual/CoreBluetooth_concepts/BestPracticesForSettingUpYourIOSDeviceAsAPeripheral/BestPracticesForSettingUpYourIOSDeviceAsAPeripheral.html#//apple_ref/doc/uid/TP40013257-CH5-SW1>`_
            - `Stack Overflow post #1 <https://stackoverflow.com/questions/25254932/can-you-pair-a-bluetooth-le-device-in-an-ios-app>`_
            - `Stack Overflow post #2 <https://stackoverflow.com/questions/47546690/ios-bluetooth-pairing-request-dialog-can-i-know-the-users-choice>`_
        """
        raise NotImplementedError("Pairing is not available in Core Bluetooth.")

    @override
    async def unpair(self) -> None:
        """
        Remove pairing information for a peripheral.

        Raises:
            NotImplementedError:
                This is not available on macOS since there is not explicit API
                to do a pairing.
        """
        raise NotImplementedError("Pairing is not available in Core Bluetooth.")

    async def _get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self.services is not None:
            return self.services

        services = BleakGATTServiceCollection()

        logger.debug("Retrieving services...")
        assert self._delegate
        cb_services = await self._delegate.discover_services(self._requested_services)

        for service in cb_services:
            serv = BleakGATTService(
                service, service.startHandle(), cb_uuid_to_str(service.UUID())
            )
            services.add_service(serv)

            serviceUUID = service.UUID().UUIDString()
            logger.debug(
                "Retrieving characteristics for service {}".format(serviceUUID)
            )
            characteristics = await self._delegate.discover_characteristics(service)

            for characteristic in characteristics:
                cUUID = characteristic.UUID().UUIDString()
                logger.debug(
                    "Retrieving descriptors for characteristic {}".format(cUUID)
                )

                char = BleakGATTCharacteristic(
                    characteristic,
                    characteristic.handle(),
                    cb_uuid_to_str(characteristic.UUID()),
                    list(gatt_char_props_to_strs(characteristic.properties())),
                    lambda: self._peripheral.maximumWriteValueLengthForType_(
                        CBCharacteristicWriteWithoutResponse
                    ),
                    serv,
                )
                services.add_characteristic(char)

                descriptors = await self._delegate.discover_descriptors(characteristic)
                for descriptor in descriptors:
                    desc = BleakGATTDescriptor(
                        descriptor,
                        int(descriptor.handle()),
                        cb_uuid_to_str(descriptor.UUID()),
                        char,
                    )
                    services.add_descriptor(desc)

        logger.debug("Services resolved for %s", str(self))
        self.services = services
        return self.services

    @override
    async def read_gatt_char(
        self, characteristic: BleakGATTCharacteristic, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to read from.

        Returns:
            (bytearray) The read data.

        """
        assert self._delegate
        output = await self._delegate.read_characteristic(
            characteristic.obj, use_cached=kwargs.get("use_cached", False)
        )
        value = bytearray(output)
        logger.debug("Read Characteristic {0} : {1}".format(characteristic.uuid, value))
        return value

    @override
    async def read_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            use_cached (bool): `False` forces Windows to read the value from the
                device again and not use its own cached value. Defaults to `False`.

        Returns:
            (bytearray) The read data.
        """
        assert self._delegate
        output = await self._delegate.read_descriptor(
            descriptor.obj, use_cached=kwargs.get("use_cached", False)
        )
        if isinstance(
            output, str
        ):  # Sometimes a `pyobjc_unicode`or `__NSCFString` is returned and they can be used as regular Python strings.
            value = bytearray(output.encode("utf-8"))
        else:  # _NSInlineData
            value = bytearray(output)  # value.getBytes_length_(None, len(value))
        logger.debug("Read Descriptor %d : %r", descriptor.handle, value)
        return value

    @override
    async def write_gatt_char(
        self, characteristic: BleakGATTCharacteristic, data: Buffer, response: bool
    ) -> None:
        value = NSData.alloc().initWithBytes_length_(data, len(data))
        await self._delegate.write_characteristic(
            characteristic.obj,
            value,
            (
                CBCharacteristicWriteWithResponse
                if response
                else CBCharacteristicWriteWithoutResponse
            ),
        )
        logger.debug(f"Write Characteristic {characteristic.uuid} : {data}")

    @override
    async def write_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, data: Buffer
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            descriptor: The descriptor to read from.
            data: The data to send (any bytes-like object).

        """
        assert self._delegate
        value = NSData.alloc().initWithBytes_length_(data, len(data))
        await self._delegate.write_descriptor(descriptor.obj, value)
        logger.debug("Write Descriptor %d : %r", descriptor.handle, data)

    @override
    async def start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: NotifyCallback,
        *,
        cb: CBStartNotifyArgs,
        **kwargs: Any,
    ) -> None:
        """
        Activate notifications/indications on a characteristic.
        """
        assert self._delegate is not None

        await self._delegate.start_notifications(
            characteristic.obj,
            callback,
            cb.get("notification_discriminator"),
        )

    @override
    async def stop_notify(self, characteristic: BleakGATTCharacteristic) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            characteristic (BleakGATTCharacteristic: The characteristic to deactivate
                notification/indication on.
        """
        assert self._delegate
        await self._delegate.stop_notifications(characteristic.obj)

    async def get_rssi(self) -> int:
        """To get RSSI value in dBm of the connected Peripheral"""
        assert self._delegate
        return int(await self._delegate.read_rssi())
