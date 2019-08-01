"""
CentralManagerDelegate will implement the CBCentralManagerDelegate protocol to
manage CoreBluetooth serivces and resources on the Central End

Created on June, 25 2019 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging
from enum import Enum
from typing import List

import objc
from Foundation import (
    NSObject,
    CBCentralManager,
    CBPeripheral,
    CBUUID,
    NSArray,
    NSDictionary,
    NSNumber,
    NSError,
)

from bleak.backends.corebluetooth.PeripheralDelegate import PeripheralDelegate

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CBCentralManagerDelegate = objc.protocolNamed("CBCentralManagerDelegate")


class CMDConnectionState(Enum):
    DISCONNECTED = 0
    PENDING = 1
    CONNECTED = 2


class CentralManagerDelegate(NSObject):
    """macOS conforming python class for managing the CentralManger for BLE"""

    ___pyobjc_protocols__ = [CBCentralManagerDelegate]

    def init(self):
        """macOS init function for NSObject"""
        self = objc.super(CentralManagerDelegate, self).init()

        if self is None:
            return None

        self.central_manager = CBCentralManager.alloc().initWithDelegate_queue_(
            self, None
        )

        self.connected_peripheral_delegate = None
        self.connected_peripheral = None
        self._connection_state = CMDConnectionState.DISCONNECTED

        self.ready = False
        self.peripheral_list = []
        self.peripheral_delegate_list = []
        self.advertisement_data_list = []

        if not self.compliant():
            logger.warning("CentralManagerDelegate is not compliant")

        return self

    # User defined functions

    def compliant(self):
        """Determins whether the class adheres to the CBCentralManagerDelegate protocol"""
        return CentralManagerDelegate.pyobjc_classMethods.conformsToProtocol_(
            CBCentralManagerDelegate
        )

    @property
    def enabled(self):
        """Check if the bluetooth device is on and running"""
        return self.central_manager.state() == 5

    @property
    def isConnected(self) -> bool:
        # Validate this
        return self.connected_peripheral != None

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
        if "service_uuids" in scan_options:
            service_uuids_str = scan_options["service_uuids"]
            service_uuids = NSArray.alloc().initWithArray_(
                list(map(string2uuid, service_uuids_str))
            )

        timeout = None
        if "timeout" in scan_options:
            timeout = scan_options["timeout"]

        self.central_manager.scanForPeripheralsWithServices_options_(
            service_uuids, None
        )

        if timeout is None or type(timeout) not in (int, float):
            return

        await asyncio.sleep(timeout)
        self.central_manager.stopScan()

        return []

    async def connect_(self, peripheral: CBPeripheral) -> bool:
        self._connection_state = CMDConnectionState.PENDING
        self.central_manager.connectPeripheral_options_(peripheral, None)

        while self._connection_state == CMDConnectionState.PENDING:
            await asyncio.sleep(0)

        self.connected_peripheral = peripheral

        return self._connection_state == CMDConnectionState.CONNECTED

    async def disconnect(self) -> bool:
        self._connection_state = CMDConnectionState.PENDING
        self.central_manager.cancelPeripheralConnection_(self.connected_peripheral)

        while self._connection_state == CMDConnectionState.PENDING:
            await asyncio.sleep(0)

        return self._connection_state == CMDConnectionState.DISCONNECTED

    # Protocol Functions

    def centralManagerDidUpdateState_(self, centralManager):
        if centralManager.state() == 0:
            logger.debug("Cannot detect bluetooth device")
        elif centralManager.state() == 1:
            logger.debug("Bluetooth is resetting")
        elif centralManager.state() == 2:
            logger.debug("Bluetooth is unsupported")
        elif centralManager.state() == 3:
            logger.debug("Bluetooth is unauthorized")
        elif centralManager.state() == 4:
            logger.debug("Bluetooth powered off")
        elif centralManager.state() == 5:
            logger.debug("Bluetooth powered on")

        self.ready = True

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary,
        RSSI: NSNumber,
    ):
        uuid_string = peripheral.identifier().UUIDString()
        if uuid_string not in list(
            map(lambda x: x.identifier().UUIDString(), self.peripheral_list)
        ):
            self.peripheral_list.append(peripheral)
            self.advertisement_data_list.append(advertisementData)
            logger.debug(
                "Discovered device {}: {} @ RSSI: {}".format(
                    uuid_string, peripheral.name() or "Unknown", RSSI
                )
            )

    def centralManager_didConnectPeripheral_(self, central, peripheral):
        logger.debug(
            "Successfully connected to device uuid {}".format(
                peripheral.identifier().UUIDString()
            )
        )
        peripheralDelegate = PeripheralDelegate.alloc().initWithPeripheral_(peripheral)
        self.connected_peripheral_delegate = peripheralDelegate
        self._connection_state = CMDConnectionState.CONNECTED

    def centralManager_didFailToConnectPeripheral_error_(
        self, centralManager: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        logger.debug(
            "Failed to connect to device uuid {}".format(
                peripheral.identifier().UUIDString()
            )
        )
        self._connection_state = CMDConnectionState.DISCONNECTED

    def centralManager_didDisconnectPeripheral_error_(
        self, central: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        logger.debug("Peripheral Device disconnected!")
        self._connection_state = CMDConnectionState.DISCONNECTED


def string2uuid(uuid_str: str) -> CBUUID:
    """Convert a string to a uuid"""
    return CBUUID.UUIDWithString_(uuid_str)
