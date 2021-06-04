"""

PeripheralDelegate

Created by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging
from typing import Callable, Any, Dict, NewType, Optional

import objc
from Foundation import NSObject, NSArray, NSData, NSError, NSString
from CoreBluetooth import (
    CBPeripheral,
    CBService,
    CBCharacteristic,
    CBDescriptor,
    CBCharacteristicWriteWithResponse,
    CBCharacteristicWriteWithoutResponse,
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

        self._service_characteristic_discovered_futures: Dict[
            NSString, asyncio.Future
        ] = {}
        self._characteristic_descriptor_discover_futures: Dict[
            NSString, asyncio.Future
        ] = {}

        self._characteristic_read_futures: Dict[NSString, asyncio.Future] = {}
        self._characteristic_write_futures: Dict[NSString, asyncio.Future] = {}

        self._descriptor_read_futures: Dict[NSString, asyncio.Future] = {}
        self._descriptor_write_futures: Dict[NSString, asyncio.Future] = {}

        self._characteristic_notify_change_futures: Dict[int, asyncio.Future] = {}
        self._characteristic_notify_callbacks: Dict[int, Callable[[str, Any], Any]] = {}

        return self

    async def discoverServices(self, use_cached: bool = True) -> NSArray:
        if self._services_discovered_future.done() and use_cached:
            return self.peripheral.services()

        future = self._event_loop.create_future()
        self._services_discovered_future = future
        self.peripheral.discoverServices_(None)
        await future

        return self.peripheral.services()

    async def discoverCharacteristics_(
        self, service: CBService, use_cached: bool = True
    ) -> NSArray:
        if service.characteristics() is not None and use_cached:
            return service.characteristics()

        sUUID = service.UUID().UUIDString()

        future = self._event_loop.create_future()
        self._service_characteristic_discovered_futures[sUUID] = future
        self.peripheral.discoverCharacteristics_forService_(None, service)
        await future

        return service.characteristics()

    async def discoverDescriptors_(
        self, characteristic: CBCharacteristic, use_cached: bool = True
    ) -> NSArray:
        if characteristic.descriptors() is not None and use_cached:
            return characteristic.descriptors()

        cUUID = characteristic.UUID().UUIDString()

        future = self._event_loop.create_future()
        self._characteristic_descriptor_discover_futures[cUUID] = future
        self.peripheral.discoverDescriptorsForCharacteristic_(characteristic)
        await future

        return characteristic.descriptors()

    async def readCharacteristic_(
        self, characteristic: CBCharacteristic, use_cached: bool = True
    ) -> NSData:
        if characteristic.value() is not None and use_cached:
            return characteristic.value()

        cUUID = characteristic.UUID().UUIDString()

        future = self._event_loop.create_future()
        self._characteristic_read_futures[cUUID] = future
        self.peripheral.readValueForCharacteristic_(characteristic)
        await asyncio.wait_for(future, timeout=5)
        if characteristic.value():
            return characteristic.value()
        else:
            return b""

    def getMtuSize(self) -> int:
        """Use type CBCharacteristicWriteWithoutResponse to get maximum write value length based on the
        the negotiated ATT MTU size. Add the ATT header length (+3) to get the actual ATT MTU size"""
        return (
            self.peripheral.maximumWriteValueLengthForType_(
                CBCharacteristicWriteWithoutResponse
            )
            + 3
        )

    async def readDescriptor_(
        self, descriptor: CBDescriptor, use_cached: bool = True
    ) -> Any:
        if descriptor.value() is not None and use_cached:
            return descriptor.value()

        dUUID = descriptor.UUID().UUIDString()

        future = self._event_loop.create_future()
        self._descriptor_read_futures[dUUID] = future
        self.peripheral.readValueForDescriptor_(descriptor)
        await future

        return descriptor.value()

    async def writeCharacteristic_value_type_(
        self,
        characteristic: CBCharacteristic,
        value: NSData,
        response: CBCharacteristicWriteType,
    ) -> bool:
        cUUID = characteristic.UUID().UUIDString()

        future = self._event_loop.create_future()
        self._characteristic_write_futures[cUUID] = future
        self.peripheral.writeValue_forCharacteristic_type_(
            value, characteristic, response
        )

        if response == CBCharacteristicWriteWithResponse:
            await future

        return True

    async def writeDescriptor_value_(
        self, descriptor: CBDescriptor, value: NSData
    ) -> bool:
        dUUID = descriptor.UUID().UUIDString()

        future = self._event_loop.create_future()
        self._descriptor_write_futures[dUUID] = future
        self.peripheral.writeValue_forDescriptor_(value, descriptor)
        await future

        return True

    async def startNotify_cb_(
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

    async def stopNotify_(self, characteristic: CBCharacteristic) -> bool:
        c_handle = characteristic.handle()
        if c_handle not in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notification never started")

        future = self._event_loop.create_future()
        self._characteristic_notify_change_futures[c_handle] = future
        self.peripheral.setNotifyValue_forCharacteristic_(False, characteristic)
        await future

        self._characteristic_notify_callbacks.pop(c_handle)

        return True

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
        sUUID = service.UUID().UUIDString()
        future = self._service_characteristic_discovered_futures.get(sUUID)
        if not future:
            logger.debug(
                f"Unexpected event didDiscoverCharacteristicsForService for {sUUID}"
            )
            return
        if error is not None:
            exception = BleakError(
                f"Failed to discover characteristics for service {sUUID}: {error}"
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
        cUUID = characteristic.UUID().UUIDString()
        future = self._characteristic_descriptor_discover_futures.get(cUUID)
        if not future:
            logger.warning(
                f"Unexpected event didDiscoverDescriptorsForCharacteristic for {cUUID}"
            )
            return
        if error is not None:
            exception = BleakError(
                f"Failed to discover descriptors for characteristic {cUUID}: {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug(f"Descriptor discovered {cUUID}")
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
        value: bytes,
        error: Optional[NSError],
    ):
        cUUID = characteristic.UUID().UUIDString()
        c_handle = characteristic.handle()

        if error is None:
            notify_callback = self._characteristic_notify_callbacks.get(c_handle)
            if notify_callback:
                notify_callback(c_handle, value)

        future = self._characteristic_read_futures.get(cUUID)
        if not future:
            return  # only expected on read
        if error is not None:
            exception = BleakError(f"Failed to read characteristic {cUUID}: {error}")
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
        dUUID = descriptor.UUID().UUIDString()
        future = self._descriptor_read_futures.get(dUUID)
        if not future:
            logger.warning("Unexpected event didUpdateValueForDescriptor")
            return
        if error is not None:
            exception = BleakError(f"Failed to read descriptor {dUUID}: {error}")
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
        cUUID = characteristic.UUID().UUIDString()
        future = self._characteristic_write_futures.get(cUUID)
        if not future:
            return  # event only expected on write with response
        if error is not None:
            exception = BleakError(f"Failed to write characteristic {cUUID}: {error}")
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
        dUUID = descriptor.UUID().UUIDString()
        future = self._desciptor_write_futures.get(dUUID)
        if not future:
            logger.warning("Unexpected event didWriteValueForDescriptor")
            return
        if error is not None:
            exception = BleakError(f"Failed to write descriptor {dUUID}: {error}")
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
        cUUID = characteristic.UUID().UUIDString()
        c_handle = characteristic.handle()
        future = self._characteristic_notify_change_futures.get(c_handle)
        if not future:
            logger.warning(
                "Unexpected event didUpdateNotificationStateForCharacteristic"
            )
            return
        if error is not None:
            exception = BleakError(
                f"Failed to update the notification status for characteristic {cUUID}: {error}"
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
