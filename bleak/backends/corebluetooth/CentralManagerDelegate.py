"""
CentralManagerDelegate will implement the CBCentralManagerDelegate protocol to
manage CoreBluetooth services and resources on the Central End

Created on June, 25 2019 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging
import platform
from enum import Enum
from typing import List

import objc
from CoreBluetooth import (
    CBManagerStateUnknown,
    CBManagerStateResetting,
    CBManagerStateUnsupported,
    CBManagerStateUnauthorized,
    CBManagerStatePoweredOff,
    CBManagerStatePoweredOn,
)
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
from libdispatch import dispatch_queue_create, DISPATCH_QUEUE_SERIAL

from bleak.backends.corebluetooth.PeripheralDelegate import PeripheralDelegate
from bleak.backends.corebluetooth.device import BLEDeviceCoreBluetooth


logger = logging.getLogger(__name__)

CBCentralManagerDelegate = objc.protocolNamed("CBCentralManagerDelegate")

_mac_version = list(map(int, platform.mac_ver()[0].split(".")))
_IS_PRE_10_13 = _mac_version[0] == 10 and _mac_version[1] < 13


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

        self.event_loop = asyncio.get_event_loop()
        self.connected_peripheral_delegate = None
        self.connected_peripheral = None
        self._connection_state = CMDConnectionState.DISCONNECTED

        self.powered_on_event = asyncio.Event()
        self.devices = {}

        self.callbacks = {}
        self.disconnected_callback = None

        if not self.compliant():
            logger.warning("CentralManagerDelegate is not compliant")

        self.central_manager = CBCentralManager.alloc().initWithDelegate_queue_(
            self, dispatch_queue_create(b"bleak.corebluetooth", DISPATCH_QUEUE_SERIAL)
        )

        return self

    # User defined functions

    def compliant(self):
        """Determines whether the class adheres to the CBCentralManagerDelegate protocol"""
        return CentralManagerDelegate.pyobjc_classMethods.conformsToProtocol_(
            CBCentralManagerDelegate
        )

    @property
    def isConnected(self) -> bool:
        return self._connection_state == CMDConnectionState.CONNECTED

    @objc.python_method
    async def wait_for_powered_on(self, timeout: float):
        """
        Waits for state to be CBManagerStatePoweredOn. This must be done before
        attempting to do anything else.

        Throws asyncio.TimeoutError if power on is not detected before timeout.
        """
        await asyncio.wait_for(self.powered_on_event.wait(), timeout)

    async def scanForPeripherals_(self, scan_options) -> List[CBPeripheral]:
        """
        Scan for peripheral devices
        scan_options = { service_uuids, timeout }
        """
        # remove old
        self.devices = {}
        service_uuids = []
        if "service_uuids" in scan_options:
            service_uuids_str = scan_options["service_uuids"]
            service_uuids = NSArray.alloc().initWithArray_(
                list(map(string2uuid, service_uuids_str))
            )

        timeout = 0
        if "timeout" in scan_options:
            timeout = float(scan_options["timeout"])

        self.central_manager.scanForPeripheralsWithServices_options_(
            service_uuids, None
        )

        if timeout > 0:
            await asyncio.sleep(timeout)

        self.central_manager.stopScan()

        # Wait a while to allow central manager to stop scanning.
        # The `isScanning` attribute is added in macOS 10.13, so before that
        # just waiting some will have to do. In 10.13+ I have never seen
        # bleak enter the while-loop, so this fix is most probably safe.
        if _IS_PRE_10_13:
            await asyncio.sleep(0.1)
        else:
            while self.central_manager.isScanning():
                await asyncio.sleep(0.1)

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

    @objc.python_method
    def did_update_state(self, centralManager):
        if centralManager.state() == CBManagerStateUnknown:
            logger.debug("Cannot detect bluetooth device")
        elif centralManager.state() == CBManagerStateResetting:
            logger.debug("Bluetooth is resetting")
        elif centralManager.state() == CBManagerStateUnsupported:
            logger.debug("Bluetooth is unsupported")
        elif centralManager.state() == CBManagerStateUnauthorized:
            logger.debug("Bluetooth is unauthorized")
        elif centralManager.state() == CBManagerStatePoweredOff:
            logger.debug("Bluetooth powered off")
        elif centralManager.state() == CBManagerStatePoweredOn:
            logger.debug("Bluetooth powered on")

        if centralManager.state() == CBManagerStatePoweredOn:
            self.powered_on_event.set()
        else:
            self.powered_on_event.clear()

    def centralManagerDidUpdateState_(self, centralManager):
        logger.debug("centralManagerDidUpdateState_")
        self.event_loop.call_soon_threadsafe(
            self.did_update_state, centralManager,
        )

    @objc.python_method
    def did_discover_peripheral(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary,
        RSSI: NSNumber,
    ):
        # Note: this function might be called several times for same device.
        # Example a first time with the following keys in advertisementData:
        # ['kCBAdvDataLocalName', 'kCBAdvDataIsConnectable', 'kCBAdvDataChannel']
        # ... and later a second time with other keys (and values) such as:
        # ['kCBAdvDataServiceUUIDs', 'kCBAdvDataIsConnectable', 'kCBAdvDataChannel']
        #
        # i.e it is best not to trust advertisementData for later use and data
        # from it should be copied.
        #
        # This behaviour could be affected by the
        # CBCentralManagerScanOptionAllowDuplicatesKey global setting.

        uuid_string = peripheral.identifier().UUIDString()

        if uuid_string in self.devices:
            device = self.devices[uuid_string]
        else:
            address = uuid_string
            name = peripheral.name() or None
            details = peripheral
            device = BLEDeviceCoreBluetooth(address, name, details)
            self.devices[uuid_string] = device

        device._rssi = float(RSSI)
        device._update(advertisementData)

        for callback in self.callbacks.values():
            if callback:
                callback(peripheral, advertisementData, RSSI)

        logger.debug(
            "Discovered device {}: {} @ RSSI: {} (kCBAdvData {})".format(
                uuid_string, device.name, RSSI, advertisementData.keys()
            )
        )

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary,
        RSSI: NSNumber,
    ):
        logger.debug("centralManager_didDiscoverPeripheral_advertisementData_RSSI_")
        self.event_loop.call_soon_threadsafe(
            self.did_discover_peripheral, central, peripheral, advertisementData, RSSI,
        )

    @objc.python_method
    def did_connect_peripheral(self, central, peripheral):
        logger.debug(
            "Successfully connected to device uuid {}".format(
                peripheral.identifier().UUIDString()
            )
        )
        peripheralDelegate = PeripheralDelegate.alloc().initWithPeripheral_(peripheral)
        self.connected_peripheral_delegate = peripheralDelegate
        self._connection_state = CMDConnectionState.CONNECTED

    def centralManager_didConnectPeripheral_(self, central, peripheral):
        logger.debug("centralManager_didConnectPeripheral_")
        self.event_loop.call_soon_threadsafe(
            self.did_connect_peripheral, central, peripheral,
        )

    @objc.python_method
    def did_fail_to_connect_peripheral(
        self, centralManager: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        logger.debug(
            "Failed to connect to device uuid {}".format(
                peripheral.identifier().UUIDString()
            )
        )
        self._connection_state = CMDConnectionState.DISCONNECTED

    def centralManager_didFailToConnectPeripheral_error_(
        self, centralManager: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        logger.debug("centralManager_didFailToConnectPeripheral_error_")
        self.event_loop.call_soon_threadsafe(
            self.did_fail_to_connect_peripheral, centralManager, peripheral, error,
        )

    @objc.python_method
    def did_disconnect_peripheral(
        self, central: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        logger.debug("Peripheral Device disconnected!")
        self._connection_state = CMDConnectionState.DISCONNECTED

        if self.disconnected_callback is not None:
            self.disconnected_callback()

    def centralManager_didDisconnectPeripheral_error_(
        self, central: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        logger.debug("centralManager_didDisconnectPeripheral_error_")
        self.event_loop.call_soon_threadsafe(
            self.did_disconnect_peripheral, central, peripheral, error,
        )


def string2uuid(uuid_str: str) -> CBUUID:
    """Convert a string to a uuid"""
    return CBUUID.UUIDWithString_(uuid_str)
