"""

PeripheralDelegate

Created by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging

from bleak.exc import BleakError
# from typing import List
import objc
from bleak.backends.corebluetooth.corebleak import CoreBleak
from Foundation import NSObject, \
        CBPeripheral, \
        CBService, \
        CBCharacteristic, \
        CBDescriptor, \
        NSData, \
        NSError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CBPeripheralDelegate = objc.protocolNamed('CBPeripheralDelegate')


class PeripheralDelegate(NSObject):
    """macOS conforming python class for managing the PeripheralDelegate for BLE"""
    ___pyobjc_protocols__ = [CBPeripheralDelegate]

    def initWithPeripheral_(self, peripheral: CBPeripheral):
        """macOS init function for NSObject"""
        self = objc.super(PeripheralDelegate, self).init()

        if self is None:
            return None

        self.peripheral = peripheral
        CoreBleak.assignPeripheralDelegate_toPeripheral_(self, self.peripheral)
        self._services_discovered = False
        self._service_characteristic_discovered_log = {}
        self._characteristic_descriptor_log = {}

        self._characteristic_value_log = {}

        if not self.compliant():
            logger.warning("PeripheralDelegate is not compliant")

        return self

    def compliant(self):
        """Determins whether the class adheres to the CBCentralManagerDelegate protocol"""
        return PeripheralDelegate.pyobjc_classMethods.conformsToProtocol_(CBPeripheralDelegate)

    async def discoverServices(self, use_cached=True) -> [CBService]:
        if self._services_discovered and ( use_cached is True ):
            return self.peripheral.services()

        self.peripheral.discoverServices_(None)

        while not self._services_discovered:
            await asyncio.sleep(0.01)

        return self.peripheral.services()

    async def discoverCharacteristics_(self, service: CBService, use_cached=True) -> [CBCharacteristic]:
        if service.characteristics() is not None and use_cached is True:
            return service.characteristics()

        serviceUUID = service.UUID().UUIDString()
        self._service_characteristic_discovered_log[serviceUUID] = False

        self.peripheral.discoverCharacteristics_forService_(None, service)

        while not self._service_characteristic_discovered_log[serviceUUID]:
            await asyncio.sleep(0.01)

        return service.characteristics()

    async def discoverDescriptors_(self, characteristic: CBCharacteristic, use_cached=True) -> [CBDescriptor]:
        if characteristic.descriptors() is not None and use_cached is True:
            return characteristic.descriptors()
        
        cUUID = characteristic.UUID().UUIDString()
        self._characteristic_descriptor_log[cUUID] = False

        self.peripheral.discoverDescriptorsForCharacteristic_(characteristic)

        while not self._characteristic_descriptor_log[cUUID]:
            await asyncio.sleep(0.01)

        return characteristic.descriptors()

    async def readCharacteristic_(self, characteristic: CBCharacteristic, use_cached=True) -> NSData:
        if characteristic.value() is not None and use_cached is True:
            return characteristic.value()

        cUUID = characteristic.UUID().UUIDString()
        self._characteristic_value_log[cUUID] = False

        self.peripheral.readValueForCharacteristic_(characteristic)

        while not self._characteristic_value_log[cUUID]:
            await asyncio.sleep(0.01)

        return characteristic.value()

    # Protocol Functions
    def peripheral_didDiscoverServices_(self, peripheral: CBPeripheral, error: NSError) -> None:
        if error is not None:
            raise BleakError(f"Failed to discover services {error}")

        logger.debug("Serivces Discovered")
        self._services_discovered = True

    def peripheral_didDiscoverCharacteristicsForService_error_(self, peripheral: CBPeripheral, service:CBService, error: NSError):
        serviceUUID = service.UUID().UUIDString()
        if error is not None:
            raise BleakError(f"Failed to discover services for service {serviceUUID}: {error}")

        logger.debug("Characteristics discovrered")
        self._service_characteristic_discovered_log[serviceUUID] = True

    def peripheral_didDiscoverDescriptorsForCharacteristic_error_(self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(f"Failed to discover descriptors for characteristic {cUUID}: {error}")

        logger.debug("Descriptor discovered")
        self._characteristic_descriptor_log[cUUID] = True

    def peripheral_didUpdateValueForCharacteristic_error_(self, peripheral: CBPeripheral, characteristic: CBCharacteristic, error: NSError):
        cUUID = characteristic.UUID().UUIDString()
        if error is not None:
            raise BleakError(f"Failed to read characteristic {cUUID}: {error}")

        logger.debug("Read characteristic value")
        self._characteristic_value_log[cUUID] = True
