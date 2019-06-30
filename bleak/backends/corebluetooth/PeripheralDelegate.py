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

        if not self.compliant():
            logger.warning("PeripheralDelegate is not compliant")

        return self

    def compliant(self):
        """Determins whether the class adheres to the CBCentralManagerDelegate protocol"""
        return PeripheralDelegate.pyobjc_classMethods.conformsToProtocol_(CBPeripheralDelegate)

    async def discoverServices(self) -> [CBService]:
        if self._services_discovered:
            return self.peripheral.services

        self.peripheral.delegate().peripheral.discoverServices_(None)

        while not self._services_discovered:
            await asyncio.sleep(0.05)

        return self.peripheral.services()

    # Protocol Functions
    def peripheral_didDiscoverServices_(self, peripheral: CBPeripheral, error: NSError) -> None:
        if error != None:
            raise BleakError(f"Failed to discover services {error}")

        logger.debug("Serivces Discovered")
        self._services_discovered = True
