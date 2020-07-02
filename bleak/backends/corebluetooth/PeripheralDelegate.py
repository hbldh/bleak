"""

PeripheralDelegate

Created by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging
from typing import Callable, Any

import objc
from Foundation import (
    NSObject,
    CBPeripheral,
    CBService,
    CBCharacteristic,
    CBDescriptor,
    NSData,
    NSError,
)
from CoreBluetooth import (
    CBCharacteristicWriteWithResponse,
    CBCharacteristicWriteWithoutResponse,
)

from bleak.exc import BleakError

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CBPeripheralDelegate = objc.protocolNamed("CBPeripheralDelegate")


class _EventDict(dict):
    def get_cleared(self, xUUID) -> asyncio.Event:
        """ Convenience method.
        Returns a cleared (False) event. Creates it if doesen't exits.
        """
        if xUUID not in self:
            # init as cleared (False)
            self[xUUID] = asyncio.Event()
        else:
            self[xUUID].clear()
        return self[xUUID]


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
        self._services_discovered_event = asyncio.Event()

        self._service_characteristic_discovered_events = _EventDict()
        self._characteristic_descriptor_discover_events = _EventDict()

        self._characteristic_read_events = _EventDict()
        self._characteristic_write_events = _EventDict()

        self._descriptor_read_events = _EventDict()
        self._descriptor_write_events = _EventDict()

        self._characteristic_notify_change_events = _EventDict()
        self._characteristic_notify_callbacks = {}

        if not self.compliant():
            logger.warning("PeripheralDelegate is not compliant")

        return self

    def compliant(self):
        """Determines whether the class adheres to the CBPeripheralDelegate protocol"""
        return PeripheralDelegate.pyobjc_classMethods.conformsToProtocol_(
            CBPeripheralDelegate
        )

    async def discoverServices(self, use_cached=True) -> [CBService]:
        event = self._services_discovered_event
        if event.is_set() and (use_cached is True):
            return self.peripheral.services()

        event.clear()
        self.peripheral.discoverServices_(None)
        # wait for peripheral_didDiscoverServices_ to set
        await event.wait()

        return self.peripheral.services()

    async def discoverCharacteristics_(
        self, service: CBService, use_cached=True
    ) -> [CBCharacteristic]:
        if service.characteristics() is not None and use_cached is True:
            return service.characteristics()

        sUUID = service.UUID().UUIDString()
        event = self._service_characteristic_discovered_events.get_cleared(sUUID)
        self.peripheral.discoverCharacteristics_forService_(None, service)
        await event.wait()

        return service.characteristics()

    async def discoverDescriptors_(
        self, characteristic: CBCharacteristic, use_cached=True
    ) -> [CBDescriptor]:
        if characteristic.descriptors() is not None and use_cached is True:
            return characteristic.descriptors()

        cUUID = characteristic.UUID().UUIDString()
        event = self._characteristic_descriptor_discover_events.get_cleared(cUUID)
        self.peripheral.discoverDescriptorsForCharacteristic_(characteristic)
        await event.wait()

        return characteristic.descriptors()

    async def readCharacteristic_(
        self, characteristic: CBCharacteristic, use_cached=True
    ) -> NSData:
        if characteristic.value() is not None and use_cached is True:
            return characteristic.value()

        cUUID = characteristic.UUID().UUIDString()

        event = self._characteristic_read_events.get_cleared(cUUID)
        self.peripheral.readValueForCharacteristic_(characteristic)
        await event.wait()

        return characteristic.value()

    async def readDescriptor_(
        self, descriptor: CBDescriptor, use_cached=True
    ) -> NSData:
        if descriptor.value() is not None and use_cached is True:
            return descriptor.value()

        dUUID = descriptor.UUID().UUIDString()

        event = self._descriptor_read_events.get_cleared(dUUID)
        self.peripheral.readValueForDescriptor_(descriptor)
        await event.wait()

        return descriptor.value()

    async def writeCharacteristic_value_type_(
        self, characteristic: CBCharacteristic, value: NSData, response: int
    ) -> bool:
        # TODO: Is the type hint for response correct? Should it be a NSInteger instead?

        cUUID = characteristic.UUID().UUIDString()

        event = self._characteristic_write_events.get_cleared(cUUID)
        self.peripheral.writeValue_forCharacteristic_type_(
            value, characteristic, response
        )

        if response == CBCharacteristicWriteWithResponse:
            await event.wait()

        return True

    async def writeDescriptor_value_(
        self, descriptor: CBDescriptor, value: NSData
    ) -> bool:
        dUUID = descriptor.UUID().UUIDString()

        event = self._descriptor_write_events.get_cleared(dUUID)
        self.peripheral.writeValue_forDescriptor_(value, descriptor)
        await event.wait()

        return True

    async def startNotify_cb_(
        self, characteristic: CBCharacteristic, callback: Callable[[str, Any], Any]
    ) -> bool:
        cUUID = characteristic.UUID().UUIDString()
        if cUUID in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notifications already started")

        self._characteristic_notify_callbacks[cUUID] = callback

        event = self._characteristic_notify_change_events.get_cleared(cUUID)
        self.peripheral.setNotifyValue_forCharacteristic_(True, characteristic)
        # wait for peripheral_didUpdateNotificationStateForCharacteristic_error_ to set event
        await event.wait()

        return True

    async def stopNotify_(self, characteristic: CBCharacteristic) -> bool:
        cUUID = characteristic.UUID().UUIDString()
        if cUUID not in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notification never started")

        event = self._characteristic_notify_change_events.get_cleared(cUUID)
        self.peripheral.setNotifyValue_forCharacteristic_(False, characteristic)
        # wait for peripheral_didUpdateNotificationStateForCharacteristic_error_ to set event
        await event.wait()

        self._characteristic_notify_callbacks.pop(cUUID)

        return True

    # Protocol Functions

    @objc.python_method
    def did_discover_services(self, peripheral: CBPeripheral, error: NSError) -> None:
        if error is not None:
            raise BleakError("Failed to discover services {}".format(error))

        logger.debug("Services discovered")
        self._services_discovered_event.set()

    def peripheral_didDiscoverServices_(
        self, peripheral: CBPeripheral, error: NSError
    ) -> None:
        logger.debug("peripheral_didDiscoverServices_")
        self._event_loop.call_soon_threadsafe(
            self.did_discover_services, peripheral, error,
        )

    @objc.python_method
    def did_discover_characteristics_for_service(
        self, peripheral: CBPeripheral, service: CBService, error: NSError
    ):
        sUUID = service.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to discover services for service {}: {}".format(sUUID, error)
            )

        logger.debug("Characteristics discovered")
        event = self._service_characteristic_discovered_events.get(sUUID)
        if event:
            event.set()
        else:
            logger.debug("Unexpected event didDiscoverCharacteristicsForService")

    def peripheral_didDiscoverCharacteristicsForService_error_(
        self, peripheral: CBPeripheral, service: CBService, error: NSError
    ):
        logger.debug("peripheral_didDiscoverCharacteristicsForService_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_discover_characteristics_for_service, peripheral, service, error,
        )

    @objc.python_method
    def did_discover_descriptors_for_characteristic(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
    ):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to discover descriptors for characteristic {}: {}".format(
                    cUUID, error
                )
            )

        logger.debug("Descriptor discovered {}".format(cUUID))
        event = self._characteristic_descriptor_discover_events.get(cUUID)
        if event:
            event.set()
        else:
            logger.warning("Unexpected event didDiscoverDescriptorsForCharacteristic")

    def peripheral_didDiscoverDescriptorsForCharacteristic_error_(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
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
        error: NSError,
    ):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to read characteristic {}: {}".format(cUUID, error)
            )

        notify_callback = self._characteristic_notify_callbacks.get(cUUID)
        if notify_callback:
            notify_callback(cUUID, value)

        logger.debug("Read characteristic value")
        event = self._characteristic_read_events.get(cUUID)
        if event:
            event.set()
        else:
            # only expected on read
            pass

    def peripheral_didUpdateValueForCharacteristic_error_(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
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
        self, peripheral: CBPeripheral, descriptor: CBDescriptor, error: NSError
    ):
        dUUID = descriptor.UUID().UUIDString()
        if error is not None:
            raise BleakError("Failed to read descriptor {}: {}".format(dUUID, error))

        logger.debug("Read descriptor value")
        event = self._descriptor_read_events.get(dUUID)
        if event:
            event.set()
        else:
            logger.warning("Unexpected event didUpdateValueForDescriptor")

    def peripheral_didUpdateValueForDescriptor_error_(
        self, peripheral: CBPeripheral, descriptor: CBDescriptor, error: NSError
    ):
        logger.debug("peripheral_didUpdateValueForDescriptor_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_update_value_for_descriptor, peripheral, descriptor, error,
        )

    @objc.python_method
    def did_write_value_for_characteristic(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
    ):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to write characteristic {}: {}".format(cUUID, error)
            )

        logger.debug("Write Characteristic Value")
        event = self._characteristic_write_events.get(cUUID)
        if event:
            event.set()
        else:
            # event only expected on write with response
            pass

    def peripheral_didWriteValueForCharacteristic_error_(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
    ):
        logger.debug("peripheral_didWriteValueForCharacteristic_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_write_value_for_characteristic, peripheral, characteristic, error,
        )

    @objc.python_method
    def did_write_value_for_descriptor(
        self, peripheral: CBPeripheral, descriptor: CBDescriptor, error: NSError
    ):
        dUUID = descriptor.UUID().UUIDString()
        if error is not None:
            raise BleakError("Failed to write descriptor {}: {}".format(dUUID, error))

        logger.debug("Write Descriptor Value")
        event = self._descriptor_write_events.get(dUUID)
        if event:
            event.set()
        else:
            logger.warning("Unexpected event didWriteValueForDescriptor")

    def peripheral_didWriteValueForDescriptor_error_(
        self, peripheral: CBPeripheral, descriptor: CBDescriptor, error: NSError
    ):
        logger.debug("peripheral_didWriteValueForDescriptor_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_write_value_for_descriptor, peripheral, descriptor, error,
        )

    @objc.python_method
    def did_update_notification_for_characteristic(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
    ):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to update the notification status for characteristic {}: {}".format(
                    cUUID, error
                )
            )
        logger.debug("Character Notify Update")

        event = self._characteristic_notify_change_events.get(cUUID)
        if event:
            event.set()
        else:
            logger.warning(
                "Unexpected event didUpdateNotificationStateForCharacteristic"
            )

    def peripheral_didUpdateNotificationStateForCharacteristic_error_(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
    ):
        logger.debug("peripheral_didUpdateNotificationStateForCharacteristic_error_")
        self._event_loop.call_soon_threadsafe(
            self.did_update_notification_for_characteristic,
            peripheral,
            characteristic,
            error,
        )
