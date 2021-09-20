"""

PeripheralDelegate

Created by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import itertools
import logging
from typing import Callable, Any, Dict, Iterable, NewType, Optional

import objc
from Foundation import NSNumber, NSObject, NSArray, NSData, NSError, NSUUID
from CoreBluetooth import (
    CBPeripheral,
    CBService,
    CBCharacteristic,
    CBDescriptor,
    CBCharacteristicWriteWithResponse,
)

from bleak.exc import BleakError

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CBPeripheralDelegate = objc.protocolNamed("CBPeripheralDelegate")

CBCharacteristicWriteType = NewType("CBCharacteristicWriteType", int)


class PeripheralDelegate(NSObject):
    """macOS conforming python class for managing the PeripheralDelegate for BLE"""

    ___pyobjc_protocols__ = [CBPeripheralDelegate]

    def initWithPeripheral_(self, peripheral: CBPeripheral):
        """macOS init function for NSObject"""
        self = objc.super(PeripheralDelegate, self).init()

        if self is None:
            return None

        self.peripheral = peripheral
        self.peripheral.setDelegate_(self)

        self._event_loop = asyncio.get_event_loop()
        self._services_discovered_future = self._event_loop.create_future()

        self._service_characteristic_discovered_futures: Dict[int, asyncio.Future] = {}
        self._characteristic_descriptor_discover_futures: Dict[int, asyncio.Future] = {}

        self._characteristic_read_futures: Dict[int, asyncio.Future] = {}
        self._characteristic_write_futures: Dict[int, asyncio.Future] = {}

        self._descriptor_read_futures: Dict[int, asyncio.Future] = {}
        self._descriptor_write_futures: Dict[int, asyncio.Future] = {}

        self._characteristic_notify_change_futures: Dict[int, asyncio.Future] = {}
        self._characteristic_notify_callbacks: Dict[int, Callable[[str, Any], Any]] = {}

        self._read_rssi_futures: Dict[NSUUID, asyncio.Future] = {}

        return self

    @objc.python_method
    def futures(self) -> Iterable[asyncio.Future]:
        """
        Gets all futures for this delegate.

        These can be used to handle any pending futures when a peripheral is disconnected.
        """
        return itertools.chain(
            (self._services_discovered_future,),
            self._service_characteristic_discovered_futures.values(),
            self._characteristic_descriptor_discover_futures.values(),
            self._characteristic_read_futures.values(),
            self._characteristic_write_futures.values(),
            self._descriptor_read_futures.values(),
            self._descriptor_write_futures.values(),
            self._characteristic_notify_change_futures.values(),
            self._read_rssi_futures.values(),
        )

    @objc.python_method
    async def discover_services(self, use_cached: bool = True) -> NSArray:
        if self._services_discovered_future.done() and use_cached:
            return self.peripheral.services()

        future = self._event_loop.create_future()
        self._services_discovered_future = future
        self.peripheral.discoverServices_(None)
        await future

        return self.peripheral.services()

    @objc.python_method
    async def discover_characteristics(
        self, service: CBService, use_cached: bool = True
    ) -> NSArray:
        if service.characteristics() is not None and use_cached:
            return service.characteristics()

        future = self._event_loop.create_future()
        self._service_characteristic_discovered_futures[service.startHandle()] = future
        self.peripheral.discoverCharacteristics_forService_(None, service)
        await future

        return service.characteristics()

    @objc.python_method
    async def discover_descriptors(
        self, characteristic: CBCharacteristic, use_cached: bool = True
    ) -> NSArray:
        if characteristic.descriptors() is not None and use_cached:
            return characteristic.descriptors()

        future = self._event_loop.create_future()
        self._characteristic_descriptor_discover_futures[
            characteristic.handle()
        ] = future
        self.peripheral.discoverDescriptorsForCharacteristic_(characteristic)
        await future

        return characteristic.descriptors()

    @objc.python_method
    async def read_characteristic(
        self, characteristic: CBCharacteristic, use_cached: bool = True
    ) -> NSData:
        if characteristic.value() is not None and use_cached:
            return characteristic.value()

        future = self._event_loop.create_future()
        self._characteristic_read_futures[characteristic.handle()] = future
        self.peripheral.readValueForCharacteristic_(characteristic)
        await asyncio.wait_for(future, timeout=5)
        if characteristic.value():
            return characteristic.value()
        else:
            return b""

    @objc.python_method
    async def read_descriptor(
        self, descriptor: CBDescriptor, use_cached: bool = True
    ) -> Any:
        if descriptor.value() is not None and use_cached:
            return descriptor.value()

        future = self._event_loop.create_future()
        self._descriptor_read_futures[descriptor.handle()] = future
        self.peripheral.readValueForDescriptor_(descriptor)
        await future

        return descriptor.value()

    @objc.python_method
    async def write_characteristic(
        self,
        characteristic: CBCharacteristic,
        value: NSData,
        response: CBCharacteristicWriteType,
    ) -> bool:
        # in CoreBluetooth there is no indication of success or failure of
        # CBCharacteristicWriteWithoutResponse
        if response == CBCharacteristicWriteWithResponse:
            future = self._event_loop.create_future()
            self._characteristic_write_futures[characteristic.handle()] = future

        self.peripheral.writeValue_forCharacteristic_type_(
            value, characteristic, response
        )

        if response == CBCharacteristicWriteWithResponse:
            await future

        return True

    @objc.python_method
    async def write_descriptor(self, descriptor: CBDescriptor, value: NSData) -> bool:
        future = self._event_loop.create_future()
        self._descriptor_write_futures[descriptor.handle()] = future
        self.peripheral.writeValue_forDescriptor_(value, descriptor)
        await future

        return True

    @objc.python_method
    async def start_notifications(
        self, characteristic: CBCharacteristic, callback: Callable[[str, Any], Any]
    ) -> bool:
        c_handle = characteristic.handle()
        if c_handle in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notifications already started")

        self._characteristic_notify_callbacks[c_handle] = callback

        future = self._event_loop.create_future()
        self._characteristic_notify_change_futures[c_handle] = future
        self.peripheral.setNotifyValue_forCharacteristic_(True, characteristic)
        await future

        return True

    @objc.python_method
    async def stop_notifications(self, characteristic: CBCharacteristic) -> bool:
        c_handle = characteristic.handle()
        if c_handle not in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notification never started")

        future = self._event_loop.create_future()
        self._characteristic_notify_change_futures[c_handle] = future
        self.peripheral.setNotifyValue_forCharacteristic_(False, characteristic)
        await future

        self._characteristic_notify_callbacks.pop(c_handle)

        return True

    @objc.python_method
    async def read_rssi(self) -> NSNumber:
        future = self._event_loop.create_future()
        self._read_rssi_futures[self.peripheral.identifier()] = future
        self.peripheral.readRSSI()
        return await future

    # Protocol Functions

    @objc.python_method
    def did_discover_services(
        self, peripheral: CBPeripheral, error: Optional[NSError]
    ) -> None:
        future = self._services_discovered_future
        if error is not None:
            exception = BleakError(f"Failed to discover services {error}")
            future.set_exception(exception)
        else:
            logger.debug("Services discovered")
            future.set_result(None)

    def peripheral_didDiscoverServices_(
        self, peripheral: CBPeripheral, error: Optional[NSError]
    ) -> None:
        logger.debug("peripheral_didDiscoverServices_")
        self._event_loop.call_soon_threadsafe(
            self.did_discover_services,
            peripheral,
            error,
        )

    @objc.python_method
    def did_discover_characteristics_for_service(
        self, peripheral: CBPeripheral, service: CBService, error: Optional[NSError]
    ):
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
            future.set_result(None)

    def peripheral_didDiscoverCharacteristicsForService_error_(
        self, peripheral: CBPeripheral, service: CBService, error: Optional[NSError]
    ):
        logger.debug("peripheral_didDiscoverCharacteristicsForService_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_discover_characteristics_for_service,
            peripheral,
            service,
            error,
        )

    @objc.python_method
    def did_discover_descriptors_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ):
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

    def peripheral_didDiscoverDescriptorsForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ):
        logger.debug("peripheral_didDiscoverDescriptorsForCharacteristic_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_discover_descriptors_for_characteristic,
            peripheral,
            characteristic,
            error,
        )

    @objc.python_method
    def did_update_value_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        value: NSData,
        error: Optional[NSError],
    ):
        c_handle = characteristic.handle()

        if error is None:
            notify_callback = self._characteristic_notify_callbacks.get(c_handle)
            if notify_callback:
                notify_callback(c_handle, bytearray(value))

        future = self._characteristic_read_futures.get(c_handle)
        if not future:
            return  # only expected on read
        if error is not None:
            exception = BleakError(f"Failed to read characteristic {c_handle}: {error}")
            future.set_exception(exception)
        else:
            logger.debug("Read characteristic value")
            future.set_result(None)

    def peripheral_didUpdateValueForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ):
        logger.debug("peripheral_didUpdateValueForCharacteristic_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_update_value_for_characteristic,
            peripheral,
            characteristic,
            characteristic.value(),
            error,
        )

    @objc.python_method
    def did_update_value_for_descriptor(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ):
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
            future.set_result(None)

    def peripheral_didUpdateValueForDescriptor_error_(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ):
        logger.debug("peripheral_didUpdateValueForDescriptor_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_update_value_for_descriptor,
            peripheral,
            descriptor,
            error,
        )

    @objc.python_method
    def did_write_value_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ):
        future = self._characteristic_write_futures.pop(characteristic.handle(), None)
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

    def peripheral_didWriteValueForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ):
        logger.debug("peripheral_didWriteValueForCharacteristic_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_write_value_for_characteristic,
            peripheral,
            characteristic,
            error,
        )

    @objc.python_method
    def did_write_value_for_descriptor(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ):
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

    def peripheral_didWriteValueForDescriptor_error_(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ):
        logger.debug("peripheral_didWriteValueForDescriptor_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_write_value_for_descriptor,
            peripheral,
            descriptor,
            error,
        )

    @objc.python_method
    def did_update_notification_for_characteristic(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ):
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

    def peripheral_didUpdateNotificationStateForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ):
        logger.debug("peripheral_didUpdateNotificationStateForCharacteristic_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_update_notification_for_characteristic,
            peripheral,
            characteristic,
            error,
        )

    @objc.python_method
    def did_read_rssi(
        self, peripheral: CBPeripheral, rssi: NSNumber, error: Optional[NSError]
    ) -> None:
        future = self._read_rssi_futures.pop(peripheral.identifier(), None)

        if not future:
            logger.warning("Unexpected event did_read_rssi")
            return

        if error is not None:
            exception = BleakError(f"Failed to read RSSI: {error}")
            future.set_exception(exception)
        else:
            future.set_result(rssi)


# peripheralDidUpdateRSSI:error: was deprecated and replaced with
# peripheral:didReadRSSI:error: in macOS 10.13
if objc.macos_available(10, 13):

    def peripheral_didReadRSSI_error_(
        self: PeripheralDelegate,
        peripheral: CBPeripheral,
        rssi: NSNumber,
        error: Optional[NSError],
    ) -> None:
        logger.debug("peripheral_didReadRSSI_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_read_rssi, peripheral, rssi, error
        )

    objc.classAddMethod(
        PeripheralDelegate,
        b"peripheral:didReadRSSI:error:",
        peripheral_didReadRSSI_error_,
    )


else:

    def peripheralDidUpdateRSSI_error_(
        self: PeripheralDelegate, peripheral: CBPeripheral, error: Optional[NSError]
    ) -> None:
        logger.debug("peripheralDidUpdateRSSI_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_read_rssi, peripheral, peripheral.RSSI(), error
        )

    objc.classAddMethod(
        PeripheralDelegate,
        b"peripheralDidUpdateRSSI:error:",
        peripheralDidUpdateRSSI_error_,
    )
