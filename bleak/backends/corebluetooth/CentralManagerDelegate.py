"""
CentralManagerDelegate will implement the CBCentralManagerDelegate protocol to
manage CoreBluetooth serivces and resources on the Central End

Created on June, 25 2019 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging
from typing import List
import objc
from Foundation import NSObject, CBCentralManager, CBPeripheral, CBUUID, NSArray, NSDictionary, NSNumber

logger = logging.getLogger(__name__)

CBCentralManagerDelegate = objc.protocolNamed('CBCentralManagerDelegate')


class CentralManagerDelegate(NSObject):
    """macOS conforming python class for managing the CentralManger for BLE"""
    ___pyobjc_protocols__ = [CBCentralManagerDelegate]

    def init(self):
        """macOS init function for NSObject"""
        self = objc.super(CentralManagerDelegate, self).init()

        if self is None:
            return None

        self.central_manager = CBCentralManager.alloc().initWithDelegate_queue_(self, None)
        self.ready = False
        self.peripheral_list = []

        if not self.compliant():
            logger.warning("CentralManagerDelegate is not compliant")

        return self

    def compliant(self):
        """Determins whether the class adheres to the CBCentralManagerDelegate protocol"""
        return CentralManagerDelegate.pyobjc_classMethods.conformsToProtocol_(CBCentralManagerDelegate)

    @property
    def enabled(self):
        """Check if the bluetooth device is on and running"""
        return self.central_manager.state() == 5

    async def is_ready(self):
        """is_ready allows an asynchronous way to wait and ensure the
        CentralManager has processed it's inputs before moving on"""
        while not self.ready:
            await asyncio.sleep(0)
        return self.ready

    async def scanForPeripherals_(self, scan_options) -> List[CBPeripheral]:
        """
        Scan for peripheral devices
        scan_options = { service_uuids, timeout }
        """
        service_uuids = []
        if 'service_uuids' in scan_options:
            service_uuids = uuidlist2nsarray(scan_options['service_uuids'])

        timeout = None
        if 'timeout' in scan_options:
            timeout = scan_options['timeout']

        self.central_manager.scanForPeripheralsWithServices_options_(service_uuids, None)

        if timeout is None or type(timeout) not in (int, float):
            return

        await asyncio.sleep(timeout)
        self.central_manager.stopScan()

        return []

    # Protocol Functions
    def centralManagerDidUpdateState_(self, centralManager):
        self.ready = True

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(self, 
                                                                     central: CBCentralManager,
                                                                     peripheral: CBPeripheral,
                                                                     advertisementData: NSDictionary,
                                                                     RSSI: NSNumber):
        self.peripheral_list.append(peripheral)
        uuid_string = peripheral.identifier().UUIDString()
        logger.debug(f"Received {uuid_string}: {peripheral.name() or 'Unknown'}")
        print("H")

def uuidlist2nsarray(uuid_list: List) -> NSArray:
    """Convert array of uuids to NSArray of CBUUIDs"""
    return NSArray.alloc().initWithArray_(list(map(string2uuid, uuid_list)))


def string2uuid(uuid_str: str) -> CBUUID:
    """Convert a string to a uuid"""
    return CBUUID.alloc().UUIDWithString_(uuid_str)
