import sys
from typing import Any, Callable, NewType, Optional, Protocol, TypeVar, Union

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
    NSObject,
    NSString,
)
from libdispatch import dispatch_queue_t

T = TypeVar("T")

Property = Union[
    Callable[[], T],  # "pyobjc" style
    T,  # "rubicon-objc" style
]

class CBManager(NSObject):
    state: Property[CBManagerState]
    authorization: Property[CBManagerAuthorization]

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
    # HACK: retrieveAddressForPeripheral_ is undocumented
    def retrieveAddressForPeripheral_(
        self, peripheral: CBPeripheral
    ) -> Optional[bytes]: ...

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
    identifier: Property[NSUUID]

class CBPeripheral(CBPeer):
    name: Property[NSString]
    delegate: Property[CBPeripheralDelegate]
    def setDelegate_(self, delegate: CBPeripheralDelegate) -> None: ...
    def discoverServices_(self, serviceUUIDs: Optional[NSArray[CBUUID]]) -> None: ...
    def discoverIncludedServices_forService_(
        self, includedServiceUUIDs: NSArray[CBService], service: CBService
    ) -> None: ...
    services: Property[NSArray[CBService]]
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
    state: Property[CBPeripheralState]
    def canSendWriteWithoutResponse(self) -> bool: ...
    def readRSSI(self) -> None: ...
    RSSI: Property[int]

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
        rssi: int,
        error: Optional[NSError],
    ) -> None: ...
    def peripheralDidUpdateName_(self, peripheral: CBPeripheral) -> None: ...
    def peripheral_didModifyServices_(
        self, peripheral: CBPeripheral, invalidatedServices: NSArray[CBService]
    ) -> None: ...

class CBAttribute(NSObject):
    UUID: Property[CBUUID]

class CBService(CBAttribute):
    peripheral: Property[CBPeripheral]
    isPrimary: Property[bool]
    characteristics: Property[NSArray[CBCharacteristic]]
    includedServices: Property[Optional[NSArray[CBService]]]
    # Undocumented property
    startHandle: Property[int]

class CBUUID(NSObject):
    @classmethod
    def UUIDWithString_(cls, theString: str) -> CBUUID: ...
    @classmethod
    def UUIDWithData_(cls, theData: NSData) -> CBUUID: ...
    @classmethod
    def UUIDWithNSUUID_(cls, theUUID: NSUUID) -> CBUUID: ...
    data: Property[NSData]
    UUIDString: Property[NSString]

class CBCharacteristic(CBAttribute):
    service: Property[CBService]
    value: Property[Optional[NSData]]
    descriptors: Property[NSArray[CBDescriptor]]
    properties: Property[CBCharacteristicProperties]
    isNotifying: Property[bool]
    # Undocumented property
    handle: Property[int]

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
    characteristic: Property[CBCharacteristic]
    value: Property[Optional[Any]]
    # Undocumented property
    handle: Property[int]
