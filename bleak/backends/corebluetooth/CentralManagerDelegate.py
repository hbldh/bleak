"""
CentralManagerDelegate will implement the CBCentralManagerDelegate protocol to
manage CoreBluetooth services and resources on the Central End

Created on June, 25 2019 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio
import logging
import weakref
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

from CoreBluetooth import (
    CBManagerStatePoweredOff,
    CBManagerStatePoweredOn,
    CBManagerStateResetting,
    CBManagerStateUnauthorized,
    CBManagerStateUnknown,
    CBManagerStateUnsupported, 
    CBCentralManagerScanOptionAllowDuplicatesKey
)

from bleak.backends.corebluetooth.device import BLEDeviceCoreBluetooth
from time import time
# Problem: Two functions reference the client (BleakClientCoreBluetooth). 
#          to get type info, they'd have to be imported.  But this file is imported from the package
#          and the client imports the CBAPP from the pacakge...So this leads to a circuar
#          import
#import bleak.backends.corebluetooth.client.BleakClientCoreBluetooth as BleakClientCoreBluetooth

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

        self._ready = False
        # Dictionary of Addresses -> Clients
        self._clients = weakref.WeakValueDictionary() 
        # scanner (did discover) callback
        self._discovercb = None
        self._filters = None
        self.devices = {}

        self.disconnected_callback = None

        if not self.compliant():
            logger.warning("CentralManagerDelegate is not compliant")

        return self

    # User defined functions
    def setdiscovercallback_(self, callback):
        if callback!=None:
            self._discovercb = weakref.WeakMethod(callback)
        else:
            self._discovercb = None


    # User defined functions
    def removeclient_(self, client):
        if client.address in self._clients:
            otherClient = self._clients[client.address]
            if id(otherClient) == id(client):
                del self._clients[client.address]

    def compliant(self):
        """Determines whether the class adheres to the CBCentralManagerDelegate protocol"""
        return CentralManagerDelegate.pyobjc_classMethods.conformsToProtocol_(
            CBCentralManagerDelegate
        )

    @property
    def enabled(self):
        """Check if the bluetooth device is on and running"""
        return self.central_manager.state() not in [CBManagerStateUnsupported, CBManagerStateUnauthorized]

    async def is_ready(self):
        """is_ready allows an asynchronous way to wait and ensure the
        CentralManager has processed it's inputs before moving on"""
        while not self._ready:
            await asyncio.sleep(0)
        return self._ready

    async def scanForPeripherals_(self, options):
        """
        Scan for peripheral devices
        
        options dictionary contains one required and one optional value:

        timeout is required
            If a number, the time in seconds to scan before returning results
            If None, then continuously scan (scan starts and must be stopped explicitly)
            
        filters is optional as are individual keys in filters
                Follows the filtering key/values used in BlueZ 
                (https://github.com/RadiusNetworks/bluez/blob/master/doc/adapter-api.txt)
            filters :{ 
                  "DuplicateData": Are duplicate records allowed (default: True)
                  "UUIDs": [  Array of String UUIDs for services of interest. Any device that advertised one of them is included]
                  "RSSI" : only include devices with a greater RSSI. 
                  "Pathloss": int minimum path loss;  Only include devices that include TX power and where
                                 TX power - RSSI > Pathloss value
            }
        """
        logger.debug("Scanning...")
        # remove old devices
        self.devices = {}

        # Scanning options cover service UUID filtering and removing duplicates
        # Device discovery will cover RSSI & Pathloss limits
        # Determine filtering data (used to start scan and validate detected devices)
        self._filters = options.get("filters",{})
        allow_duplicates = 1 if self._filters.get("DuplicateData", False) == True else 0

        service_uuids = []
        if "UUIDs" in self._filters:
            service_uuids_str = self._filters["UUIDs"]
            service_uuids = NSArray.alloc().initWithArray_(
                list(map(string2uuid, service_uuids_str))
            )

        self.central_manager.scanForPeripheralsWithServices_options_(
            service_uuids, NSDictionary.dictionaryWithDictionary_({CBCentralManagerScanOptionAllowDuplicatesKey:allow_duplicates})
            # service_uuids, {CBCentralManagerScanOptionAllowDuplicatesKey:allow_duplicates}
        )
            # service_uuids, NSDictionary.dictionaryWithDictionary_({CBCentralManagerScanOptionAllowDuplicatesKey:allow_duplicates})

        timeout = options["timeout"]
        if timeout is not None:
            await asyncio.sleep(float(timeout))
            # Request scan stop and wait for confirmation that it's done
            self.central_manager.stopScan()
            while self.central_manager.isScanning():
                await asyncio.sleep(0.05)

    async def connect_(self, client) -> bool:
        client._connection_state = CMDConnectionState.PENDING
        # Add client to map (before connect)
        self._clients[client.address] = client
        self.central_manager.connectPeripheral_options_(client._peripheral, None)

        start = time()
        while client._connection_state == CMDConnectionState.PENDING and time()-start<client._timeout:
            await asyncio.sleep(0)

        return client._connection_state == CMDConnectionState.CONNECTED

    async def disconnect_(self, client) -> bool:
        client._connection_state = CMDConnectionState.PENDING
        self.central_manager.cancelPeripheralConnection_(client._peripheral)

        while client._connection_state == CMDConnectionState.PENDING:
            await asyncio.sleep(0)

        return client._connection_state == CMDConnectionState.DISCONNECTED

    # Protocol Functions

    def centralManagerDidUpdateState_(self, centralManager):    
        self._ready = False
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
            self._ready = True

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
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
        logger.debug("Discovered device {}: {} @ RSSI: {} (kCBAdvData {})".format(
                uuid_string, peripheral.name() or None, RSSI, advertisementData.keys()))

        # Filtering 
        min_rssi = self._filters.get("RSSI", None)
        max_pathloss = self._filters.get("Pathloss", None)

        rssi = float(RSSI)
        if min_rssi is not None and rssi<min_rssi:
            logger.debug("Device doesn't meet minimum RSSI  ({} < {})".format(rssi, min_rssi))
            return
        # Compute path loss if there's a TX 

        if "CBAdvertisementDataTxPowerLevelKey" in advertisementData:
            tx_power_level = float(advertisementData["CBAdvertisementDataTxPowerLevelKey"])
            pathloss = tx_power_level - rssi 
            if pathloss > max_pathloss:
                logger.debug("Device pathloss too great  (tx ({}) - rssi ({}) > {})".format(tx_power_level, rssi, pathloss))
                return

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

        # This is where a scanner callback should happen. 
        logger.warning("calling discovery callback with: {0}".format(device))
        if self._discovercb != None:
            (self._discovercb())(device)

    def centralManager_didConnectPeripheral_(self, central, peripheral):
        address = peripheral.identifier().UUIDString()
        logger.debug(
            "Successfully connected to device uuid {}".format(
                address
            )
        )
        # If there's a client, update it
        if address in self._clients:
            client = self._clients[address]
            client._connection_state = CMDConnectionState.CONNECTED

    def centralManager_didFailToConnectPeripheral_error_(
        self, centralManager: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        address = peripheral.identifier().UUIDString()
        logger.debug(
            "Failed to connect to device uuid {}".format(
                address
            )
        )
        # If there's a client, update it
        if address in self._clients:
            client = self._clients[address]
            client._connection_state = CMDConnectionState.DISCONNECTED

    def centralManager_didDisconnectPeripheral_error_(
        self, central: CBCentralManager, peripheral: CBPeripheral, error: NSError
    ):
        address = peripheral.identifier().UUIDString()
        logger.debug(
            "Peripheral Device disconnected! {}".format(
                address
            )
        )
        # If there's a client, update it
        if address in self._clients:
            client = self._clients[address]
            client._connection_state = CMDConnectionState.DISCONNECTED
            client.did_disconnect()

def string2uuid(uuid_str: str) -> CBUUID:
    """Convert a string to a uuid"""
    return CBUUID.UUIDWithString_(uuid_str)
