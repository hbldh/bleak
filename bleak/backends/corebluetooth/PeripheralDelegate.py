"""

PeripheralDelegate

Created by kevincar <kevincarrolldavis@gmail.com>

"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import asyncio
import itertools
import logging
from collections.abc import Iterable
from typing import Any, Optional

import objc
from CoreBluetooth import (
    CBUUID,
    CBCharacteristic,
    CBCharacteristicWriteType,
    CBCharacteristicWriteWithResponse,
    CBDescriptor,
    CBPeripheral,
    CBService,
)
from Foundation import NSUUID, NSArray, NSData, NSError, NSNumber, NSObject

from bleak._compat import Self
from bleak._compat import timeout as async_timeout
from bleak.args.corebluetooth import NotificationDiscriminator
from bleak.backends._utils import try_call_soon_threadsafe
from bleak.backends.client import NotifyCallback
from bleak.exc import BleakError

logger = logging.getLogger(__name__)


CBPeripheralDelegate = objc.protocolNamed("CBPeripheralDelegate")


class ObjcPeripheralDelegate(NSObject, protocols=[CBPeripheralDelegate]):
    """
    CoreBluetooth peripheral manager delegate for bridging callbacks to asyncio.
    """

    def initWithPyDelegate_(self, py_delegate: PeripheralDelegate) -> Optional[Self]:
        """macOS init function for NSObject"""
        self = objc.super(ObjcPeripheralDelegate, self).init()  # type: ignore[assignment]

        if self is None:
            return None

        self.py_delegate = py_delegate

        return self

    # Protocol Functions

    def peripheral_didDiscoverServices_(
        self, peripheral: CBPeripheral, error: Optional[NSError]
    ) -> None:
        logger.debug("peripheral_didDiscoverServices_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_discover_services,
            peripheral,
            peripheral.services(),
            error,
        )

    def peripheral_didDiscoverIncludedServicesForService_error_(
        self, peripheral: CBPeripheral, service: CBService, error: Optional[NSError]
    ) -> None:
        logger.debug("peripheral_didDiscoverIncludedServicesForService_error_")
        # Currently not used in Bleak

    def peripheral_didDiscoverCharacteristicsForService_error_(
        self, peripheral: CBPeripheral, service: CBService, error: Optional[NSError]
    ) -> None:
        logger.debug("peripheral_didDiscoverCharacteristicsForService_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_discover_characteristics_for_service,
            peripheral,
            service,
            service.characteristics(),
            error,
        )

    def peripheral_didDiscoverDescriptorsForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didDiscoverDescriptorsForCharacteristic_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_discover_descriptors_for_characteristic,
            peripheral,
            characteristic,
            error,
        )

    def peripheral_didUpdateValueForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didUpdateValueForCharacteristic_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_update_value_for_characteristic,
            peripheral,
            characteristic,
            characteristic.value(),
            error,
        )

    def peripheral_didUpdateValueForDescriptor_error_(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didUpdateValueForDescriptor_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_update_value_for_descriptor,
            peripheral,
            descriptor,
            descriptor.value(),
            error,
        )

    def peripheral_didWriteValueForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didWriteValueForCharacteristic_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_write_value_for_characteristic,
            peripheral,
            characteristic,
            error,
        )

    def peripheral_didWriteValueForDescriptor_error_(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didWriteValueForDescriptor_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_write_value_for_descriptor,
            peripheral,
            descriptor,
            error,
        )

    def peripheralIsReadyToSendWriteWithoutResponse_(
        self, peripheral: CBPeripheral
    ) -> None:
        logger.debug("peripheralIsReadyToSendWriteWithoutResponse_")
        # Currently not used in Bleak

    def peripheral_didUpdateNotificationStateForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didUpdateNotificationStateForCharacteristic_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_update_notification_for_characteristic,
            peripheral,
            characteristic,
            error,
        )

    def peripheral_didReadRSSI_error_(
        self,
        peripheral: CBPeripheral,
        rssi: NSNumber,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didReadRSSI_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_read_rssi,
            peripheral,
            int(rssi),
            error,
        )

    # Bleak currently doesn't use the callbacks below other than for debug logging

    def peripheralDidUpdateName_(self, peripheral: CBPeripheral) -> None:
        logger.debug("peripheralDidUpdateName_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_update_name,
            peripheral,
            peripheral.name(),
        )

    def peripheral_didModifyServices_(
        self, peripheral: CBPeripheral, invalidatedServices: NSArray[CBService]
    ) -> None:
        logger.debug("peripheral_didModifyServices_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_modify_services,
            peripheral,
            invalidatedServices,
        )


class PeripheralDelegate:
    """macOS conforming python class for managing the PeripheralDelegate for BLE"""

    def __init__(self, peripheral: CBPeripheral) -> None:
        delegate = ObjcPeripheralDelegate.alloc().initWithPyDelegate_(self)
        assert delegate is not None
        self.objc_delegate = delegate

        self.peripheral = peripheral
        self.peripheral.setDelegate_(self.objc_delegate)

        self.event_loop = asyncio.get_running_loop()
        self._services_discovered_future = self.event_loop.create_future()

        self._service_characteristic_discovered_futures: dict[
            int, asyncio.Future[NSArray[CBCharacteristic]]
        ] = {}
        self._characteristic_descriptor_discover_futures: dict[
            int, asyncio.Future[None]
        ] = {}

        self._characteristic_read_futures: dict[int, asyncio.Future[NSData]] = {}
        self._characteristic_write_futures: dict[int, asyncio.Future[None]] = {}

        self._descriptor_read_futures: dict[int, asyncio.Future[NSObject]] = {}
        self._descriptor_write_futures: dict[int, asyncio.Future[None]] = {}

        self._characteristic_notify_change_futures: dict[int, asyncio.Future[None]] = {}
        self._characteristic_notify_callbacks: dict[int, NotifyCallback] = {}
        self._characteristic_notification_discriminators: dict[
            int, Optional[NotificationDiscriminator]
        ] = {}

        self._read_rssi_futures: dict[NSUUID, asyncio.Future[int]] = {}

    def futures(self) -> Iterable[asyncio.Future[Any]]:
        """
        Gets all futures for this delegate.

        These can be used to handle any pending futures when a peripheral is disconnected.
        """
        services_discovered_future = (
            (self._services_discovered_future,)
            if hasattr(self, "_services_discovered_future")
            else ()
        )

        return itertools.chain(
            services_discovered_future,
            self._service_characteristic_discovered_futures.values(),
            self._characteristic_descriptor_discover_futures.values(),
            self._characteristic_read_futures.values(),
            self._characteristic_write_futures.values(),
            self._descriptor_read_futures.values(),
            self._descriptor_write_futures.values(),
            self._characteristic_notify_change_futures.values(),
            self._read_rssi_futures.values(),
        )

    async def discover_services(
        self, services: Optional[NSArray[CBUUID]] = None
    ) -> NSArray[CBService]:
        future = self.event_loop.create_future()

        self._services_discovered_future = future
        try:
            self.peripheral.discoverServices_(services)
            return await future
        finally:
            del self._services_discovered_future

    async def discover_characteristics(
        self, service: CBService
    ) -> NSArray[CBCharacteristic]:
        future = self.event_loop.create_future()

        self._service_characteristic_discovered_futures[service.startHandle()] = future
        try:
            self.peripheral.discoverCharacteristics_forService_(None, service)
            return await future
        finally:
            del self._service_characteristic_discovered_futures[service.startHandle()]

    async def discover_descriptors(
        self, characteristic: CBCharacteristic
    ) -> NSArray[CBDescriptor]:
        future = self.event_loop.create_future()

        self._characteristic_descriptor_discover_futures[characteristic.handle()] = (
            future
        )
        try:
            self.peripheral.discoverDescriptorsForCharacteristic_(characteristic)
            await future
        finally:
            del self._characteristic_descriptor_discover_futures[
                characteristic.handle()
            ]

        return characteristic.descriptors()

    async def read_characteristic(
        self,
        characteristic: CBCharacteristic,
        use_cached: bool,
        timeout: int = 20,
    ) -> NSData:
        value = characteristic.value()
        if value is not None and use_cached:
            return value

        future = self.event_loop.create_future()

        self._characteristic_read_futures[characteristic.handle()] = future

        try:
            self.peripheral.readValueForCharacteristic_(characteristic)
            async with async_timeout(timeout):
                return await future
        finally:
            del self._characteristic_read_futures[characteristic.handle()]

    async def read_descriptor(
        self, descriptor: CBDescriptor, use_cached: bool = True
    ) -> Any:
        value = descriptor.value()
        if value is not None and use_cached:
            return value

        future = self.event_loop.create_future()

        self._descriptor_read_futures[descriptor.handle()] = future
        try:
            self.peripheral.readValueForDescriptor_(descriptor)
            return await future
        finally:
            del self._descriptor_read_futures[descriptor.handle()]

    async def write_characteristic(
        self,
        characteristic: CBCharacteristic,
        value: NSData,
        response: CBCharacteristicWriteType,
    ) -> None:
        # in CoreBluetooth there is no indication of success or failure of
        # CBCharacteristicWriteWithoutResponse
        if response == CBCharacteristicWriteWithResponse:
            future = self.event_loop.create_future()

            self._characteristic_write_futures[characteristic.handle()] = future
            try:
                self.peripheral.writeValue_forCharacteristic_type_(
                    value, characteristic, response
                )
                await future
            finally:
                del self._characteristic_write_futures[characteristic.handle()]
        else:
            self.peripheral.writeValue_forCharacteristic_type_(
                value, characteristic, response
            )

    async def write_descriptor(self, descriptor: CBDescriptor, value: NSData) -> None:
        future = self.event_loop.create_future()

        self._descriptor_write_futures[descriptor.handle()] = future
        try:
            self.peripheral.writeValue_forDescriptor_(value, descriptor)
            await future
        finally:
            del self._descriptor_write_futures[descriptor.handle()]

    async def start_notifications(
        self,
        characteristic: CBCharacteristic,
        callback: NotifyCallback,
        notification_discriminator: Optional[NotificationDiscriminator] = None,
    ) -> None:
        c_handle = characteristic.handle()
        if c_handle in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notifications already started")

        self._characteristic_notify_callbacks[c_handle] = callback
        self._characteristic_notification_discriminators[c_handle] = (
            notification_discriminator
        )

        future = self.event_loop.create_future()

        self._characteristic_notify_change_futures[c_handle] = future
        try:
            self.peripheral.setNotifyValue_forCharacteristic_(True, characteristic)
            await future
        finally:
            del self._characteristic_notify_change_futures[c_handle]

    async def stop_notifications(self, characteristic: CBCharacteristic) -> None:
        c_handle = characteristic.handle()
        if c_handle not in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notification never started")

        future = self.event_loop.create_future()

        self._characteristic_notify_change_futures[c_handle] = future
        try:
            self.peripheral.setNotifyValue_forCharacteristic_(False, characteristic)
            await future
        finally:
            del self._characteristic_notify_change_futures[c_handle]

        self._characteristic_notify_callbacks.pop(c_handle)
        self._characteristic_notification_discriminators.pop(c_handle)

    async def read_rssi(self) -> int:
        future = self.event_loop.create_future()

        self._read_rssi_futures[self.peripheral.identifier()] = future
        try:
            self.peripheral.readRSSI()
            return await future
        finally:
            del self._read_rssi_futures[self.peripheral.identifier()]

    # Protocol Functions

    def did_discover_services(
        self,
        peripheral: CBPeripheral,
        services: NSArray[CBService],
        error: Optional[NSError],
    ) -> None:
        future = self._services_discovered_future
        if error is not None:
            exception = BleakError(f"Failed to discover services {error}")
            future.set_exception(exception)
        else:
            logger.debug("Services discovered")
            future.set_result(services)

    def did_discover_characteristics_for_service(
        self,
        peripheral: CBPeripheral,
        service: CBService,
        characteristics: NSArray[CBCharacteristic],
        error: Optional[NSError],
    ) -> None:
        future = self._service_characteristic_discovered_futures.get(
            service.startHandle()
        )
        if not future:
            logger.debug(
                f"Unexpected event didDiscoverCharacteristicsForService for {service.startHandle()}"
            )
            return
        if error is not None:
            exception = BleakError(
                f"Failed to discover characteristics for service {service.startHandle()}: {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug("Characteristics discovered")
            future.set_result(characteristics)

    def did_discover_descriptors_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None:
        future = self._characteristic_descriptor_discover_futures.get(
            characteristic.handle()
        )
        if not future:
            logger.warning(
                f"Unexpected event didDiscoverDescriptorsForCharacteristic for {characteristic.handle()}"
            )
            return
        if error is not None:
            exception = BleakError(
                f"Failed to discover descriptors for characteristic {characteristic.handle()}: {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug(f"Descriptor discovered {characteristic.handle()}")
            future.set_result(None)

    def did_update_value_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        value: Optional[NSData],
        error: Optional[NSError],
    ) -> None:
        c_handle = characteristic.handle()

        future = self._characteristic_read_futures.get(c_handle)

        # If error is set, then we know this was a read response.
        # Otherwise, if there is a pending read request, we can't tell if this is a read response or notification.
        # If the user provided a notification discriminator, we can use that to
        # identify if this callback is due to a notification by analyzing the value.
        # If not, and there is a future (pending read request), we assume it is a read response but can't know for sure.
        if not error:
            assert value is not None

            notification_discriminator = (
                self._characteristic_notification_discriminators.get(c_handle)
            )
            if not future or (
                notification_discriminator and notification_discriminator(bytes(value))
            ):
                notify_callback = self._characteristic_notify_callbacks.get(c_handle)

                if notify_callback:
                    notify_callback(bytearray(value))
                    return

        if not future:
            logger.warning(
                "Unexpected event didUpdateValueForCharacteristic for 0x%04x with value: %r and error: %r",
                c_handle,
                value,
                error,
            )
            return

        if error is not None:
            exception = BleakError(f"Failed to read characteristic {c_handle}: {error}")
            future.set_exception(exception)
        else:
            logger.debug("Read characteristic value")
            assert value is not None
            future.set_result(value)

    def did_update_value_for_descriptor(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        value: Optional[Any],
        error: Optional[NSError],
    ) -> None:
        future = self._descriptor_read_futures.get(descriptor.handle())
        if not future:
            logger.warning("Unexpected event didUpdateValueForDescriptor")
            return
        if error is not None:
            exception = BleakError(
                f"Failed to read descriptor {descriptor.handle()}: {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug("Read descriptor value")
            assert value is not None
            future.set_result(value)

    def did_write_value_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None:
        future = self._characteristic_write_futures.get(characteristic.handle(), None)
        if not future:
            return  # event only expected on write with response
        if error is not None:
            exception = BleakError(
                f"Failed to write characteristic {characteristic.handle()}: {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug("Write Characteristic Value")
            future.set_result(None)

    def did_write_value_for_descriptor(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ) -> None:
        future = self._descriptor_write_futures.get(descriptor.handle())
        if not future:
            logger.warning("Unexpected event didWriteValueForDescriptor")
            return
        if error is not None:
            exception = BleakError(
                f"Failed to write descriptor {descriptor.handle()}: {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug("Write Descriptor Value")
            future.set_result(None)

    def did_update_notification_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None:
        c_handle = characteristic.handle()
        future = self._characteristic_notify_change_futures.get(c_handle)
        if not future:
            logger.warning(
                "Unexpected event didUpdateNotificationStateForCharacteristic"
            )
            return
        if error is not None:
            exception = BleakError(
                f"Failed to update the notification status for characteristic {c_handle}: {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug("Character Notify Update")
            future.set_result(None)

    def did_read_rssi(
        self, peripheral: CBPeripheral, rssi: int, error: Optional[NSError]
    ) -> None:
        future = self._read_rssi_futures.get(peripheral.identifier(), None)

        if not future:
            logger.warning("Unexpected event did_read_rssi")
            return

        if error is not None:
            exception = BleakError(f"Failed to read RSSI: {error}")
            future.set_exception(exception)
        else:
            future.set_result(rssi)

    # Bleak currently doesn't use the callbacks below other than for debug logging

    def did_update_name(self, peripheral: CBPeripheral, name: str) -> None:
        logger.debug(f"name of {peripheral.identifier()} changed to {name}")

    def did_modify_services(
        self, peripheral: CBPeripheral, invalidated_services: NSArray[CBService]
    ) -> None:
        logger.debug(
            f"{peripheral.identifier()} invalidated services: {invalidated_services}"
        )
