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

from bleak.exc import BleakError

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CBPeripheralDelegate = objc.protocolNamed("CBPeripheralDelegate")


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

        self._services_discovered = False

        self._service_characteristic_discovered_log = {}
        self._characteristic_descriptor_log = {}

        self._characteristic_value_log = {}
        self._descriptor_value_log = {}

        self._characteristic_write_log = {}
        self._descriptor_write_log = {}

        self._characteristic_notify_log = {}
        self._characteristic_notify_status = {}
        self._characteristic_notify_callbacks = {}

        if not self.compliant():
            logger.warning("PeripheralDelegate is not compliant")

        return self

    def compliant(self):
        """Determins whether the class adheres to the CBCentralManagerDelegate protocol"""
        return PeripheralDelegate.pyobjc_classMethods.conformsToProtocol_(
            CBPeripheralDelegate
        )

    async def discoverServices(self, use_cached=True) -> [CBService]:
        if self._services_discovered and (use_cached is True):
            return self.peripheral.services()

        self.peripheral.discoverServices_(None)

        while not self._services_discovered:
            await asyncio.sleep(0.01)

        return self.peripheral.services()

    async def discoverCharacteristics_(
        self, service: CBService, use_cached=True
    ) -> [CBCharacteristic]:
        if service.characteristics() is not None and use_cached is True:
            return service.characteristics()

        serviceUUID = service.UUID().UUIDString()
        self._service_characteristic_discovered_log[serviceUUID] = False

        self.peripheral.discoverCharacteristics_forService_(None, service)

        while not self._service_characteristic_discovered_log[serviceUUID]:
            await asyncio.sleep(0.01)

        return service.characteristics()

    async def discoverDescriptors_(
        self, characteristic: CBCharacteristic, use_cached=True
    ) -> [CBDescriptor]:
        if characteristic.descriptors() is not None and use_cached is True:
            return characteristic.descriptors()

        cUUID = characteristic.UUID().UUIDString()
        self._characteristic_descriptor_log[cUUID] = False

        self.peripheral.discoverDescriptorsForCharacteristic_(characteristic)

        while not self._characteristic_descriptor_log[cUUID]:
            await asyncio.sleep(0.01)

        return characteristic.descriptors()

    async def readCharacteristic_(
        self, characteristic: CBCharacteristic, use_cached=True
    ) -> NSData:
        if characteristic.value() is not None and use_cached is True:
            return characteristic.value()

        cUUID = characteristic.UUID().UUIDString()
        self._characteristic_value_log[cUUID] = False

        self.peripheral.readValueForCharacteristic_(characteristic)

        while not self._characteristic_value_log[cUUID]:
            await asyncio.sleep(0.01)

        return characteristic.value()

    async def readDescriptor_(
        self, descriptor: CBDescriptor, use_cached=True
    ) -> NSData:
        if descriptor.value() is not None and use_cached is True:
            return descriptor.value()

        dUUID = descriptor.UUID().UUIDString()
        self._descriptor_value_log[dUUID] = False

        self.peripheral.readValueForDescriptor_(descriptor)

        while not self._descriptor_value_log[dUUID]:
            await asyncio.sleep(0.01)

        return descriptor.value()

    async def writeCharacteristic_value_(
        self, characteristic: CBCharacteristic, value: NSData
    ) -> bool:

        cUUID = characteristic.UUID().UUIDString()
        self._characteristic_write_log[cUUID] = False

        self.peripheral.writeValue_forCharacteristic_type_(value, characteristic, 0)

        while not self._characteristic_write_log[cUUID]:
            await asyncio.sleep(0.01)

        return True

    async def writeDescriptor_value_(
        self, descriptor: CBDescriptor, value: NSData
    ) -> bool:
        dUUID = descriptor.UUID().UUIDString()
        self._descriptor_write_log[dUUID] = False

        self.peripheral.writeValue_forDescriptor_(value, descriptor)

        while not self._descriptor_write_log[dUUID]:
            await asyncio.sleep(0.01)

        return True

    async def startNotify_cb_(
        self, characteristic: CBCharacteristic, callback: Callable[[str, Any], Any]
    ) -> bool:
        cUUID = characteristic.UUID().UUIDString()
        self._characteristic_notify_log[cUUID] = False
        self._characteristic_notify_callbacks[cUUID] = callback

        self.peripheral.setNotifyValue_forCharacteristic_(True, characteristic)

        while not self._characteristic_notify_log[cUUID]:
            await asyncio.sleep(0.01)

        self._characteristic_notify_status[cUUID] = True
        return True

    async def stopNotify_(self, characteristic: CBCharacteristic) -> bool:
        cUUID = characteristic.UUID().UUIDString()
        self._characteristic_notify_log[cUUID] = False

        self.peripheral.setNotifyValue_forCharacteristic_(False, characteristic)

        while not self._characteristic_notify_log[cUUID]:
            await asyncio.sleep(0.01)

        self._characteristic_notify_status = False
        return True

    # Protocol Functions
    def peripheral_didDiscoverServices_(
        self, peripheral: CBPeripheral, error: NSError
    ) -> None:
        if error is not None:
            raise BleakError("Failed to discover services {}".format(error))

        logger.debug("Services discovered")
        self._services_discovered = True

    def peripheral_didDiscoverCharacteristicsForService_error_(
        self, peripheral: CBPeripheral, service: CBService, error: NSError
    ):
        serviceUUID = service.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to discover services for service {}: {}".format(
                    serviceUUID, error
                )
            )

        logger.debug("Characteristics discovered")
        self._service_characteristic_discovered_log[serviceUUID] = True

    def peripheral_didDiscoverDescriptorsForCharacteristic_error_(
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
        self._characteristic_descriptor_log[cUUID] = True

    def peripheral_didUpdateValueForCharacteristic_error_(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
    ):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to read characteristic {}: {}".format(cUUID, error)
            )

        if (
            cUUID in self._characteristic_notify_status
            and self._characteristic_notify_status[cUUID]
        ):
            self._characteristic_notify_callbacks[cUUID](cUUID, characteristic.value())

        logger.debug("Read characteristic value")
        self._characteristic_value_log[cUUID] = True

    def peripheral_didUpdateValueForDescriptor_error_(
        self, peripheral: CBPeripheral, descriptor: CBDescriptor, error: NSError
    ):
        dUUID = descriptor.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to read characteristic {}: {}".format(dUUID, error)
            )

        logger.debug("Read descriptor value")
        self._descriptor_value_log[dUUID] = True

    def peripheral_didWriteValueForCharacteristic_error_(
        self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError
    ):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(
                "Failed to write characteristic {}: {}".format(cUUID, error)
            )

        logger.debug("Write Characteristic Value")
        self._characteristic_write_log[cUUID] = True

    def peripheral_didWriteValueForDescriptor_error_(
        self, peripheral: CBPeripheral, descriptor: CBDescriptor, error: NSError
    ):
        dUUID = descriptor.UUID().UUIDString()
        if error is not None:
            raise BleakError("Failed to write descriptor {}: {}".format(dUUID, error))

        logger.debug("Write Descriptor Value")
        self._descriptor_write_log[dUUID] = True

    def peripheral_didUpdateNotificationStateForCharacteristic_error_(
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
        self._characteristic_notify_log[cUUID] = True
