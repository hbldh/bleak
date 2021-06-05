"""
CentralManagerDelegate will implement the CBCentralManagerDelegate protocol to
manage CoreBluetooth services and resources on the Central End

Created on June, 25 2019 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging
import platform
import threading
from typing import Any, Callable, Dict, List, Optional

import objc
from CoreBluetooth import (
    CBCentralManager,
    CBManagerStatePoweredOff,
    CBManagerStatePoweredOn,
    CBManagerStateResetting,
    CBManagerStateUnauthorized,
    CBManagerStateUnknown,
    CBManagerStateUnsupported,
    CBPeripheral,
    CBUUID,
)
from Foundation import (
    NSArray,
    NSDictionary,
    NSError,
    NSNumber,
    NSObject,
    NSUUID,
)
from libdispatch import dispatch_queue_create, DISPATCH_QUEUE_SERIAL

from bleak.backends.corebluetooth.device import BLEDeviceCoreBluetooth
from bleak.exc import BleakError

logger = logging.getLogger(__name__)
CBCentralManagerDelegate = objc.protocolNamed("CBCentralManagerDelegate")

try:
    _mac_version = list(map(int, platform.mac_ver()[0].split(".")))
    _IS_PRE_10_13 = _mac_version[0] == 10 and _mac_version[1] < 13
except Exception:
    _mac_version = ""
    _IS_PRE_10_13 = False

DisconnectCallback = Callable[[], None]


class CentralManagerDelegate(NSObject):
    """macOS conforming python class for managing the CentralManger for BLE"""

    ___pyobjc_protocols__ = [CBCentralManagerDelegate]

    def init(self) -> Optional["CentralManagerDelegate"]:
        """macOS init function for NSObject"""
        self = objc.super(CentralManagerDelegate, self).init()

        if self is None:
            return None

        self.event_loop = asyncio.get_event_loop()
        self._connect_futures: Dict[NSUUID, asyncio.Future] = {}

        self.devices: Dict[str, BLEDeviceCoreBluetooth] = {}

        self.callbacks: Dict[
            int, Callable[[CBPeripheral, Dict[str, Any], int], None]
        ] = {}
        self._disconnect_callbacks: Dict[NSUUID, DisconnectCallback] = {}
        self._disconnect_futures: Dict[NSUUID, asyncio.Future] = {}

        self._did_update_state_event = threading.Event()
        self.central_manager = CBCentralManager.alloc().initWithDelegate_queue_(
            self, dispatch_queue_create(b"bleak.corebluetooth", DISPATCH_QUEUE_SERIAL)
        )

        # according to CoreBluetooth docs, it is not valid to call CBCentral
        # methods until the centralManagerDidUpdateState_() delegate method
        # is called and the current state is CBManagerStatePoweredOn.
        # It doesn't take long for the callback to occur, so we should be able
        # to do a blocking wait here without anyone complaining.
        self._did_update_state_event.wait(1)

        if self.central_manager.state() == CBManagerStateUnsupported:
            raise BleakError("BLE is unsupported")

        if self.central_manager.state() != CBManagerStatePoweredOn:
            raise BleakError("Bluetooth device is turned off")

        return self

    # User defined functions

    @objc.python_method
    def start_scan(self, scan_options) -> None:
        # remove old
        self.devices = {}
        service_uuids = None
        if "service_uuids" in scan_options:
            service_uuids_str = scan_options["service_uuids"]
            service_uuids = NSArray.alloc().initWithArray_(
                list(map(CBUUID.UUIDWithString_, service_uuids_str))
            )

        self.central_manager.scanForPeripheralsWithServices_options_(
            service_uuids, None
        )

    @objc.python_method
    async def stop_scan(self) -> List[CBPeripheral]:
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

    @objc.python_method
    async def scanForPeripherals_(self, scan_options) -> List[CBPeripheral]:
        """
        Scan for peripheral devices
        scan_options = { service_uuids, timeout }
        """

        self.start_scan(scan_options)
        await asyncio.sleep(float(scan_options.get("timeout", 0.0)))
        return await self.stop_scan()

    @objc.python_method
    async def connect(
        self,
        peripheral: CBPeripheral,
        disconnect_callback: DisconnectCallback,
        timeout=10.0,
    ) -> None:
        try:
            self._disconnect_callbacks[peripheral.identifier()] = disconnect_callback
            future = self.event_loop.create_future()
            self._connect_futures[peripheral.identifier()] = future
            self.central_manager.connectPeripheral_options_(peripheral, None)
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.debug(f"Connection timed out after {timeout} seconds.")
            del self._disconnect_callbacks[peripheral.identifier()]
            future = self.event_loop.create_future()
            self._disconnect_futures[peripheral.identifier()] = future
            self.central_manager.cancelPeripheralConnection_(peripheral)
            await future
            raise

    @objc.python_method
    async def disconnect(self, peripheral: CBPeripheral) -> None:
        future = self.event_loop.create_future()
        self._disconnect_futures[peripheral.identifier()] = future
        self.central_manager.cancelPeripheralConnection_(peripheral)
        await future
        del self._disconnect_callbacks[peripheral.identifier()]

    # Protocol Functions

    def centralManagerDidUpdateState_(self, centralManager: CBCentralManager) -> None:
        logger.debug("centralManagerDidUpdateState_")
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

        self._did_update_state_event.set()

    @objc.python_method
    def did_discover_peripheral(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary,
        RSSI: NSNumber,
    ) -> None:
        # Note: this function might be called several times for same device.
        # This can happen for instance when an active scan is done, and the
        # second call with contain the data from the BLE scan response.
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
            # It could be the device did not have a name previously but now it does.
            if peripheral.name():
                device.name = peripheral.name()
        else:
            address = uuid_string
            name = peripheral.name() or None
            details = peripheral
            device = BLEDeviceCoreBluetooth(address, name, details, delegate=self)
            self.devices[uuid_string] = device

        device._update(advertisementData)
        device._update_rssi(RSSI)

        for callback in self.callbacks.values():
            if callback:
                callback(peripheral, advertisementData, RSSI)

        logger.debug(
            "Discovered device {}: {} @ RSSI: {} (kCBAdvData {}) and Central: {}".format(
                uuid_string, device.name, RSSI, advertisementData.keys(), central
            )
        )

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary,
        RSSI: NSNumber,
    ) -> None:
        logger.debug("centralManager_didDiscoverPeripheral_advertisementData_RSSI_")
        self.event_loop.call_soon_threadsafe(
            self.did_discover_peripheral,
            central,
            peripheral,
            advertisementData,
            RSSI,
        )

    @objc.python_method
    def did_connect_peripheral(
        self, central: CBCentralManager, peripheral: CBPeripheral
    ) -> None:
        future = self._connect_futures.pop(peripheral.identifier(), None)
        if future is not None:
            future.set_result(True)

    def centralManager_didConnectPeripheral_(
        self, central: CBCentralManager, peripheral: CBPeripheral
    ) -> None:
        logger.debug("centralManager_didConnectPeripheral_")
        self.event_loop.call_soon_threadsafe(
            self.did_connect_peripheral,
            central,
            peripheral,
        )

    @objc.python_method
    def did_fail_to_connect_peripheral(
        self,
        centralManager: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        future = self._connect_futures.pop(peripheral.identifier(), None)
        if future is not None:
            if error is not None:
                future.set_exception(BleakError(f"failed to connect: {error}"))
            else:
                future.set_result(False)

    def centralManager_didFailToConnectPeripheral_error_(
        self,
        centralManager: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        logger.debug("centralManager_didFailToConnectPeripheral_error_")
        self.event_loop.call_soon_threadsafe(
            self.did_fail_to_connect_peripheral,
            centralManager,
            peripheral,
            error,
        )

    @objc.python_method
    def did_disconnect_peripheral(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        logger.debug("Peripheral Device disconnected!")

        future = self._disconnect_futures.pop(peripheral.identifier(), None)
        if future is not None:
            if error is not None:
                future.set_exception(BleakError(f"disconnect failed: {error}"))
            else:
                future.set_result(None)

        callback = self._disconnect_callbacks.get(peripheral.identifier())
        if callback is not None:
            callback()

    def centralManager_didDisconnectPeripheral_error_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        logger.debug("centralManager_didDisconnectPeripheral_error_")
        self.event_loop.call_soon_threadsafe(
            self.did_disconnect_peripheral,
            central,
            peripheral,
            error,
        )
