import sys
from typing import Any, NewType, Optional, Protocol

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

from rubicon.objc.api import NSArray, NSData, NSDictionary, NSNumber, NSObject, NSString

from .Foundation import NSUUID, NSError, NSErrorDomain
from .libdispatch import dispatch_queue_t

CBErrorDomain: NSErrorDomain
CBATTErrorDomain: NSErrorDomain

CBManagerState = NewType("CBManagerState", int)
CBManagerStateUnknown: CBManagerState
CBManagerStateResetting: CBManagerState
CBManagerStateUnsupported: CBManagerState
CBManagerStateUnauthorized: CBManagerState
CBManagerStatePoweredOff: CBManagerState
CBManagerStatePoweredOn: CBManagerState

CBManagerAuthorization = NewType("CBManagerAuthorization", int)
CBManagerAuthorizationNotDetermined: CBManagerAuthorization
CBManagerAuthorizationRestricted: CBManagerAuthorization
CBManagerAuthorizationDenied: CBManagerAuthorization
CBManagerAuthorizationAllowedAlways: CBManagerAuthorization

CBCharacteristicWriteType = NewType("CBCharacteristicWriteType", int)
CBCharacteristicWriteWithResponse: CBCharacteristicWriteType
CBCharacteristicWriteWithoutResponse: CBCharacteristicWriteType

CBPeripheralState = NewType("CBPeripheralState", int)
CBPeripheralStateDisconnected: CBPeripheralState
CBPeripheralStateConnecting: CBPeripheralState
CBPeripheralStateConnected: CBPeripheralState
CBPeripheralStateDisconnecting: CBPeripheralState

class CBUUID(NSObject):
    @classmethod
    def UUIDWithString_(cls, theString: str) -> CBUUID: ...
    @classmethod
    def UUIDWithData_(cls, theData: NSData) -> CBUUID: ...
    @classmethod
    def UUIDWithNSUUID_(cls, theUUID: NSUUID) -> CBUUID: ...
    @property
    def data(self) -> NSData: ...
    @property
    def UUIDString(self) -> NSString: ...

class CBManager(NSObject):
    @property
    def state(self) -> CBManagerState: ...
    @property
    def authorization(self) -> CBManagerAuthorization: ...

CBCentralManagerFeature = NewType("CBCentralManagerFeature", int)

class CBCentralManager(CBManager):
    @classmethod
    def initWithDelegate_queue_(
        cls,
        delegate: CBCentralManagerDelegate,
        queue: dispatch_queue_t,
    ) -> Self: ...
    @classmethod
    def initWithDelegate_queue_options_(
        cls,
        delegate: CBCentralManagerDelegate,
        queue: dispatch_queue_t,
        options: NSDictionary[str, Any],
    ) -> Optional[Self]: ...
    def connectPeripheral_options_(
        self,
        peripheral: CBPeripheral,
        options: Optional[NSDictionary[str, Any]],
    ) -> None: ...
    def cancelPeripheralConnection_(self, peripheral: CBPeripheral) -> None: ...
    def retrieveConnectedPeripheralsWithServices_(
        self, serviceUUIDs: NSArray[CBUUID]
    ) -> NSArray[CBPeripheral]: ...
    def retrievePeripheralsWithIdentifiers_(
        self, serviceUUIDs: NSArray[CBUUID]
    ) -> NSArray[CBPeripheral]: ...
    def scanForPeripheralsWithServices_options_(
        self,
        serviceUUIDs: Optional[NSArray[CBUUID]],
        options: Optional[NSDictionary[str, Any]],
    ) -> None: ...
    def stopScan(self) -> None: ...
    @property
    def isScanning(self) -> bool: ...
    @classmethod
    def supportsFeatures(cls, features: CBCentralManagerFeature) -> bool: ...
    def delegate(self) -> Optional[CBCentralManagerDelegate]: ...
    def registerForConnectionEventsWithOptions_(
        self, options: NSDictionary[str, Any]
    ) -> None: ...
    # Undocumented method
    def retrieveAddressForPeripheral_(
        self, peripheral: CBPeripheral
    ) -> Optional[NSData]: ...

class CBAttribute(NSObject):
    @property
    def UUID(self) -> CBUUID: ...

CBCharacteristicProperties = NewType("CBCharacteristicProperties", int)

class CBCharacteristic(CBAttribute):
    @property
    def service(self) -> CBService: ...
    @property
    def value(self) -> Optional[NSData]: ...
    @property
    def descriptors(self) -> NSArray[CBDescriptor]: ...
    @property
    def properties(self) -> CBCharacteristicProperties: ...
    @property
    def isNotifying(self) -> bool: ...
    # Undocumented property
    @property
    def handle(self) -> int: ...

class CBDescriptor(CBAttribute):
    @property
    def characteristic(self) -> CBCharacteristic: ...
    @property
    def value(self) -> Optional[Any]: ...
    # Undocumented property
    @property
    def handle(self) -> int: ...

class CBPeer(NSObject):
    @property
    def identifier(self) -> NSUUID: ...

class CBPeripheral(CBPeer):
    @property
    def name(self) -> NSString: ...
    @property
    def delegate(self) -> CBPeripheralDelegate: ...
    def setDelegate_(self, delegate: CBPeripheralDelegate) -> None: ...
    def discoverServices_(self, serviceUUIDs: Optional[NSArray[CBUUID]]) -> None: ...
    def discoverIncludedServices_forService_(
        self, includedServiceUUIDs: NSArray[CBService], service: CBService
    ) -> None: ...
    @property
    def services(self) -> NSArray[CBService]: ...
    def discoverCharacteristics_forService_(
        self, characteristicUUIDs: Optional[NSArray[CBUUID]], service: CBService
    ) -> None: ...
    def discoverDescriptorsForCharacteristic_(
        self, characteristic: CBCharacteristic
    ) -> None: ...
    def readValueForCharacteristic_(self, characteristic: CBCharacteristic) -> None: ...
    def readValueForDescriptor_(self, descriptor: CBDescriptor) -> None: ...
    def writeValue_forCharacteristic_type_(
        self,
        data: NSData,
        characteristic: CBCharacteristic,
        type: CBCharacteristicWriteType,
    ) -> None: ...
    def writeValue_forDescriptor_(
        self, data: NSData, descriptor: CBDescriptor
    ) -> None: ...
    def maximumWriteValueLengthForType_(
        self, type: CBCharacteristicWriteType
    ) -> int: ...
    def setNotifyValue_forCharacteristic_(
        self, enabled: bool, characteristic: CBCharacteristic
    ) -> None: ...
    @property
    def state(self) -> CBPeripheralState: ...
    def canSendWriteWithoutResponse(self) -> bool: ...
    def readRSSI(self) -> None: ...
    @property
    def RSSI(self) -> int: ...

class CBService(CBAttribute):
    @property
    def peripheral(self) -> CBPeripheral: ...
    @property
    def isPrimary(self) -> bool: ...
    @property
    def characteristics(self) -> NSArray[CBCharacteristic]: ...
    @property
    def includedServices(self) -> Optional[NSArray[CBService]]: ...
    # Undocumented property
    @property
    def startHandle(self) -> int: ...

class CBCentralManagerDelegate(Protocol):
    def centralManagerDidUpdateState_(
        self, centralManager: CBCentralManager
    ) -> None: ...
    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        advertisementData: NSDictionary[str, Any],
        RSSI: NSNumber,
    ) -> None: ...
    def centralManager_didConnectPeripheral_(
        self, central: CBCentralManager, peripheral: CBPeripheral
    ) -> None: ...
    def centralManager_didFailToConnectPeripheral_error_(
        self,
        centralManager: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None: ...
    def centralManager_didDisconnectPeripheral_error_(
        self,
        central: CBCentralManager,
        peripheral: CBPeripheral,
        error: Optional[NSError],
    ) -> None: ...

class CBPeripheralDelegate(Protocol):
    def peripheral_didDiscoverServices_(
        self, peripheral: CBPeripheral, error: Optional[NSError]
    ) -> None: ...
    def peripheral_didDiscoverIncludedServicesForService_error_(
        self, peripheral: CBPeripheral, service: CBService, error: Optional[NSError]
    ) -> None: ...
    def peripheral_didDiscoverCharacteristicsForService_error_(
        self, peripheral: CBPeripheral, service: CBService, error: Optional[NSError]
    ) -> None: ...
    def peripheral_didDiscoverDescriptorsForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None: ...
    def peripheral_didUpdateValueForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None: ...
    def peripheral_didUpdateValueForDescriptor_error_(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ) -> None: ...
    def peripheral_didWriteValueForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None: ...
    def peripheral_didWriteValueForDescriptor_error_(
        self,
        peripheral: CBPeripheral,
        descriptor: CBDescriptor,
        error: Optional[NSError],
    ) -> None: ...
    def peripheralIsReadyToSendWriteWithoutResponse_(
        self, peripheral: CBPeripheral
    ) -> None: ...
    def peripheral_didUpdateNotificationStateForCharacteristic_error_(
        self,
        peripheral: CBPeripheral,
        characteristic: CBCharacteristic,
        error: Optional[NSError],
    ) -> None: ...
    def peripheral_didReadRSSI_error_(
        self,
        peripheral: CBPeripheral,
        rssi: NSNumber,
        error: Optional[NSError],
    ) -> None: ...
    def peripheralDidUpdateName_(self, peripheral: CBPeripheral) -> None: ...
    def peripheral_didModifyServices_(
        self, peripheral: CBPeripheral, invalidatedServices: NSArray[CBService]
    ) -> None: ...

CBUUIDCharacteristicExtendedPropertiesString: NSString
CBUUIDCharacteristicUserDescriptionString: NSString
CBUUIDClientCharacteristicConfigurationString: NSString
CBUUIDServerCharacteristicConfigurationString: NSString
CBUUIDCharacteristicFormatString: NSString
CBUUIDCharacteristicAggregateFormatString: NSString
CBUUIDL2CAPPSMCharacteristicString: NSString
