import sys
from typing import Any, NewType, Optional, Protocol, TypeVar

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

from Foundation import (
    NSUUID,
    NSArray,
    NSData,
    NSDictionary,
    NSError,
    NSNumber,
    NSObject,
    NSString,
)
from libdispatch import dispatch_queue_t

class CBManager(NSObject):
    def state(self) -> CBManagerState: ...
    def authorization(self) -> CBManagerAuthorization: ...

TCBCentralManager = TypeVar("TCBCentralManager", bound=CBCentralManager)

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
    def isScanning(self) -> bool: ...
    @classmethod
    def supportsFeatures(cls, features: CBCentralManagerFeature) -> bool: ...
    def delegate(self) -> Optional[CBCentralManagerDelegate]: ...
    def registerForConnectionEventsWithOptions_(
        self, options: NSDictionary[str, Any]
    ) -> None: ...

CBConnectPeripheralOptionNotifyOnConnectionKey: str
CBConnectPeripheralOptionNotifyOnDisconnectionKey: str
CBConnectPeripheralOptionNotifyOnNotificationKey: str
CBConnectPeripheralOptionEnableTransportBridgingKey: str
CBConnectPeripheralOptionRequiresANCS: str
CBConnectPeripheralOptionStartDelayKey: str

CBCentralManagerScanOptionAllowDuplicatesKey: str
CBCentralManagerScanOptionSolicitedServiceUUIDsKey: str

CBCentralManagerFeature = NewType("CBCentralManagerFeature", int)

CBCentralManagerFeatureExtendedScanAndConnect: CBCentralManagerFeature

CBManagerState = NewType("CBManagerState", int)

CBManagerStatePoweredOff: CBManagerState
CBManagerStatePoweredOn: CBManagerState
CBManagerStateResetting: CBManagerState
CBManagerStateUnauthorized: CBManagerState
CBManagerStateUnknown: CBManagerState
CBManagerStateUnsupported: CBManagerState

CBManagerAuthorization = NewType("CBManagerAuthorization", int)

CBManagerAuthorizationAllowedAlways: CBManagerAuthorization
CBManagerAuthorizationDenied: CBManagerAuthorization
CBManagerAuthorizationNotDetermined: CBManagerAuthorization
CBManagerAuthorizationRestricted: CBManagerAuthorization

CBConnectionEvent = NewType("CBConnectionEvent", int)

CBConnectionEventPeerConnected: CBConnectionEvent
CBConnectionEventPeerDisconnected: CBConnectionEvent

class CBConnectionEventMatchingOption(str): ...

CBConnectionEventMatchingOptionPeripheralUUIDs: CBConnectionEventMatchingOption
CBConnectionEventMatchingOptionServiceUUIDs: CBConnectionEventMatchingOption

class CBCentralManagerDelegate(Protocol): ...

class CBPeer(NSObject):
    def identifier(self) -> NSUUID: ...

class CBPeripheral(CBPeer):
    def name(self) -> NSString: ...
    def delegate(self) -> CBPeripheralDelegate: ...
    def setDelegate_(self, delegate: CBPeripheralDelegate) -> None: ...
    def discoverServices_(self, serviceUUIDs: Optional[NSArray[CBUUID]]) -> None: ...
    def discoverIncludedServices_forService_(
        self, includedServiceUUIDs: NSArray[CBService], service: CBService
    ) -> None: ...
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
    def state(self) -> CBPeripheralState: ...
    def canSendWriteWithoutResponse(self) -> bool: ...
    def readRSSI(self) -> None: ...
    def RSSI(self) -> NSNumber: ...

CBCharacteristicWriteType = NewType("CBCharacteristicWriteType", int)

CBCharacteristicWriteWithResponse: CBCharacteristicWriteType
CBCharacteristicWriteWithoutResponse: CBCharacteristicWriteType

CBPeripheralState = NewType("CBPeripheralState", int)

CBPeripheralStateDisconnected: CBPeripheralState
CBPeripheralStateConnecting: CBPeripheralState
CBPeripheralStateConnected: CBPeripheralState
CBPeripheralStateDisconnecting: CBPeripheralState

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

class CBAttribute(NSObject):
    def UUID(self) -> CBUUID: ...

class CBService(CBAttribute):
    def peripheral(self) -> CBPeripheral: ...
    def isPrimary(self) -> bool: ...
    def characteristics(self) -> NSArray[CBCharacteristic]: ...
    def includedServices(self) -> Optional[NSArray[CBService]]: ...
    # Undocumented property
    def startHandle(self) -> int: ...

class CBUUID(NSObject):
    @classmethod
    def UUIDWithString_(cls, theString: str) -> CBUUID: ...
    @classmethod
    def UUIDWithData_(cls, theData: NSData) -> CBUUID: ...
    @classmethod
    def UUIDWithNSUUID_(cls, theUUID: NSUUID) -> CBUUID: ...
    def data(self) -> NSData: ...
    def UUIDString(self) -> NSString: ...

class CBCharacteristic(CBAttribute):
    def service(self) -> CBService: ...
    def value(self) -> Optional[NSData]: ...
    def descriptors(self) -> NSArray[CBDescriptor]: ...
    def properties(self) -> CBCharacteristicProperties: ...
    def isNotifying(self) -> bool: ...
    # Undocumented property
    def handle(self) -> int: ...

CBCharacteristicProperties = NewType("CBCharacteristicProperties", int)

CBCharacteristicPropertyBroadcast: CBCharacteristicProperties
CBCharacteristicPropertyRead: CBCharacteristicProperties
CBCharacteristicPropertyWriteWithoutResponse: CBCharacteristicProperties
CBCharacteristicPropertyWrite: CBCharacteristicProperties
CBCharacteristicPropertyNotify: CBCharacteristicProperties
CBCharacteristicPropertyIndicate: CBCharacteristicProperties
CBCharacteristicPropertyAuthenticatedSignedWrites: CBCharacteristicProperties
CBCharacteristicPropertyExtendedProperties: CBCharacteristicProperties
CBCharacteristicPropertyNotifyEncryptionRequired: CBCharacteristicProperties
CBCharacteristicPropertyIndicateEncryptionRequired: CBCharacteristicProperties

class CBDescriptor(CBAttribute):
    def characteristic(self) -> CBCharacteristic: ...
    def value(self) -> Optional[Any]: ...
    # Undocumented property
    def handle(self) -> int: ...
