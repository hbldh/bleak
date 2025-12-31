# Created on June, 25 2019 by kevincar <kevincarrolldavis@gmail.com>
"""
CentralManagerDelegate will implement the CBCentralManagerDelegate protocol to
manage CoreBluetooth services and resources on the Central End
"""
from __future__ import annotations

import sys
import weakref
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import asyncio
import logging
from collections.abc import Callable
from typing import Any, Optional, TypedDict, cast

import objc
from CoreBluetooth import (
    CBUUID,
    CBCentralManager,
    CBManagerAuthorizationDenied,
    CBManagerAuthorizationRestricted,
    CBManagerStatePoweredOff,
    CBManagerStatePoweredOn,
    CBManagerStateResetting,
    CBManagerStateUnauthorized,
    CBManagerStateUnknown,
    CBManagerStateUnsupported,
    CBPeripheral,
)
from Foundation import (
    NSUUID,
    NSArray,
    NSData,
    NSDictionary,
    NSError,
    NSKeyValueChangeNewKey,
    NSKeyValueObservingOptionNew,
    NSNumber,
    NSObject,
    NSString,
)
from libdispatch import DISPATCH_QUEUE_SERIAL, dispatch_queue_create

from bleak._compat import Self
from bleak._compat import timeout as async_timeout
from bleak.backends._utils import try_call_soon_threadsafe
from bleak.exc import (
    BleakBluetoothNotAvailableError,
    BleakBluetoothNotAvailableReason,
    BleakError,
)

logger = logging.getLogger(__name__)
CBCentralManagerDelegate = objc.protocolNamed("CBCentralManagerDelegate")


DisconnectCallback = Callable[[], None]


class CBAdvertisementData(TypedDict, total=False):
    kCBAdvDataLocalName: NSString
    kCBAdvDataManufacturerData: NSData
    kCBAdvDataServiceData: dict[CBUUID, NSData]
    kCBAdvDataServiceUUIDs: NSArray[CBUUID]
    kCBAdvertisementDataOverflowServiceUUIDsKey: NSArray[CBUUID]
    kCBAdvDataTxPowerLevel: NSNumber
    kCBAdvertisementDataIsConnectable: NSNumber
    kCBAdvDataOverflowServiceUUIDs: NSArray[CBUUID]


class ObjcCentralManagerDelegate(NSObject, protocols=[CBCentralManagerDelegate]):
    """
    CoreBluetooth central manager delegate for bridging callbacks to asyncio.
    """

    def initWithPyDelegate_(
        self, py_delegate: CentralManagerDelegate
    ) -> Optional[Self]:
        """macOS init function for NSObject"""
        self = objc.super(ObjcCentralManagerDelegate, self).init()  # type: ignore[assignment]

        if self is None:
            return None

        self.py_delegate = py_delegate

        return self

    # User defined functions

    def observeValueForKeyPath_ofObject_change_context_(
        self,
        keyPath: NSString,
        object: Any,
        change: NSDictionary[str, Any],
        context: int,
    ) -> None:
        logger.debug("'%s' changed", keyPath)

        if keyPath != "isScanning":
            return

        is_scanning = bool(change[NSKeyValueChangeNewKey])
        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.changed_is_scanning,
            is_scanning,
        )

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

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_update_state_event.set,
        )

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary[str, Any],
        RSSI: NSNumber,
    ) -> None:
        logger.debug("centralManager_didDiscoverPeripheral_advertisementData_RSSI_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_discover_peripheral,
            central,
            peripheral,
            advertisementData,
            RSSI,
        )

    def centralManager_didConnectPeripheral_(
        self, central: CBCentralManager, peripheral: CBPeripheral
    ) -> None:
        logger.debug("centralManager_didConnectPeripheral_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_connect_peripheral,
            central,
            peripheral,
        )

    def centralManager_didFailToConnectPeripheral_error_(
        self,
        centralManager: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        logger.debug("centralManager_didFailToConnectPeripheral_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_fail_to_connect_peripheral,
            centralManager,
            peripheral,
            error,
        )

    def centralManager_didDisconnectPeripheral_error_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        logger.debug("centralManager_didDisconnectPeripheral_error_")

        try_call_soon_threadsafe(
            self.py_delegate.event_loop,
            self.py_delegate.did_disconnect_peripheral,
            central,
            peripheral,
            error,
        )


class CentralManagerDelegate:
    """
    macOS conforming python class for managing the CentralManger for BLE

    Before this object can be used, the :method:`wait_until_ready` method has to
    be called. This can take a while, when the OS asks the user for permissions.
    """

    def __init__(self) -> None:
        """macOS init function for NSObject"""
        delegate = ObjcCentralManagerDelegate.alloc().initWithPyDelegate_(self)
        assert delegate is not None
        self.objc_delegate = delegate

        self.event_loop = asyncio.get_running_loop()
        self._connect_futures: dict[NSUUID, asyncio.Future[bool]] = {}

        self.callbacks: dict[
            int,
            Callable[[CBPeripheral, CBAdvertisementData, NSNumber], None] | None,
        ] = {}
        self._disconnect_callbacks: dict[NSUUID, DisconnectCallback] = {}
        self._disconnect_futures: dict[NSUUID, asyncio.Future[None]] = {}

        self.did_update_state_event = asyncio.Event()
        self.central_manager = CBCentralManager.alloc().initWithDelegate_queue_(
            self.objc_delegate,
            dispatch_queue_create(b"bleak.corebluetooth", DISPATCH_QUEUE_SERIAL),
        )

        self.central_manager.addObserver_forKeyPath_options_context_(
            self.objc_delegate, "isScanning", NSKeyValueObservingOptionNew, 0
        )
        weakref.finalize(
            self,
            self.central_manager.removeObserver_forKeyPath_,
            self.objc_delegate,
            "isScanning",
        )

        self._did_start_scanning_event: Optional[asyncio.Event] = None
        self._did_stop_scanning_event: Optional[asyncio.Event] = None

    # User defined functions
    @objc.python_method
    async def wait_until_ready(self):
        # According to CoreBluetooth docs, it is not valid to call CBCentral
        # methods until the centralManagerDidUpdateState_() delegate method
        # is called and the current state is CBManagerStatePoweredOn.
        # Wait until the callback occurs. This normally should not take too long,
        # but if the app currently has no permission to access the Bluetooth peripheral,
        # there is automatically a dialog shown by the OS. The user has to accept or deny
        # the Bluetooth access. This may take infinite time until the user clicks something.
        await self.did_update_state_event.wait()

        state = self.central_manager.state()
        if state == CBManagerStateUnsupported:
            raise BleakBluetoothNotAvailableError(
                "Bluetooth is unsupported",
                BleakBluetoothNotAvailableReason.NO_BLUETOOTH,
            )
        elif state == CBManagerStateUnauthorized:
            authorization = self.central_manager.authorization()
            if authorization == CBManagerAuthorizationDenied:
                raise BleakBluetoothNotAvailableError(
                    "Bluetooth access is denied by the user for the current application. Check macOS privacy settings.",
                    BleakBluetoothNotAvailableReason.DENIED_BY_USER,
                )
            elif authorization == CBManagerAuthorizationRestricted:
                raise BleakBluetoothNotAvailableError(
                    "Bluetooth access is restricted for the current application, e.g. by parental controls. Ask the admin to remove this restriction.",
                    BleakBluetoothNotAvailableReason.DENIED_BY_SYSTEM,
                )
            else:
                raise BleakBluetoothNotAvailableError(
                    "Bluetooth is not authorized for an unknown reason. Check macOS privacy settings.",
                    BleakBluetoothNotAvailableReason.DENIED_BY_UNKNOWN,
                )
        elif state == CBManagerStatePoweredOff:
            raise BleakBluetoothNotAvailableError(
                "Bluetooth device is turned off",
                BleakBluetoothNotAvailableReason.POWERED_OFF,
            )
        elif state == CBManagerStateResetting:
            raise BleakBluetoothNotAvailableError(
                "Connection to the Bluetooth system service was lost. Currently trying to reconnect...",
                BleakBluetoothNotAvailableReason.UNKNOWN,
            )
        elif state != CBManagerStatePoweredOn:
            raise BleakBluetoothNotAvailableError(
                "Bluetooth state is unknwon",
                BleakBluetoothNotAvailableReason.UNKNOWN,
            )

    async def start_scan(self, service_uuids: Optional[list[str]]) -> None:
        _service_uuids = (
            NSArray[CBUUID]
            .alloc()
            .initWithArray_(list(map(CBUUID.UUIDWithString_, service_uuids)))
            if service_uuids
            else None
        )

        self.central_manager.scanForPeripheralsWithServices_options_(
            _service_uuids, None
        )

        event = asyncio.Event()
        self._did_start_scanning_event = event
        if not self.central_manager.isScanning():
            await event.wait()

    async def stop_scan(self) -> None:
        self.central_manager.stopScan()

        event = asyncio.Event()
        self._did_stop_scanning_event = event
        if self.central_manager.isScanning():
            await event.wait()

    async def connect(
        self,
        peripheral: CBPeripheral,
        disconnect_callback: DisconnectCallback,
        timeout: float = 10.0,
    ) -> None:
        try:
            self._disconnect_callbacks[peripheral.identifier()] = disconnect_callback
            future = self.event_loop.create_future()

            self._connect_futures[peripheral.identifier()] = future
            try:
                self.central_manager.connectPeripheral_options_(peripheral, None)
                async with async_timeout(timeout):
                    await future
            finally:
                del self._connect_futures[peripheral.identifier()]

        except asyncio.TimeoutError:
            logger.debug(f"Connection timed out after {timeout} seconds.")
            del self._disconnect_callbacks[peripheral.identifier()]
            future = self.event_loop.create_future()

            self._disconnect_futures[peripheral.identifier()] = future
            try:
                self.central_manager.cancelPeripheralConnection_(peripheral)
                await future
            finally:
                del self._disconnect_futures[peripheral.identifier()]

            raise

    async def disconnect(self, peripheral: CBPeripheral) -> None:
        future = self.event_loop.create_future()

        self._disconnect_futures[peripheral.identifier()] = future
        try:
            self.central_manager.cancelPeripheralConnection_(peripheral)
            await future
        finally:
            del self._disconnect_futures[peripheral.identifier()]

    def changed_is_scanning(self, is_scanning: bool) -> None:
        if is_scanning:
            if self._did_start_scanning_event:
                self._did_start_scanning_event.set()
        else:
            if self._did_stop_scanning_event:
                self._did_stop_scanning_event.set()

    # Protocol Functions

    def did_discover_peripheral(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary[str, Any],
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

        for callback in self.callbacks.values():
            if callback:
                callback(peripheral, cast(CBAdvertisementData, advertisementData), RSSI)

        logger.debug(
            "Discovered device %s: %s @ RSSI: %d (kCBAdvData %r) and Central: %r",
            uuid_string,
            peripheral.name(),
            RSSI,
            advertisementData.keys(),
            central,
        )

    def did_connect_peripheral(
        self, central: CBCentralManager, peripheral: CBPeripheral
    ) -> None:
        future = self._connect_futures.get(peripheral.identifier(), None)
        if future is not None:
            future.set_result(True)

    def did_fail_to_connect_peripheral(
        self,
        centralManager: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        future = self._connect_futures.get(peripheral.identifier(), None)
        if future is not None:
            if error is not None:
                future.set_exception(BleakError(f"failed to connect: {error}"))
            else:
                future.set_result(False)

    def did_disconnect_peripheral(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None:
        logger.debug("Peripheral Device disconnected!")

        future = self._disconnect_futures.get(peripheral.identifier(), None)
        if future is not None:
            if error is not None:
                future.set_exception(BleakError(f"disconnect failed: {error}"))
            else:
                future.set_result(None)

        callback = self._disconnect_callbacks.pop(peripheral.identifier(), None)

        if callback is not None:
            callback()
