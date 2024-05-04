from typing import Any, NewType, Optional, Type, TypeVar

from ..Foundation import (
    NSUUID,
    NSArray,
    NSData,
    NSDictionary,
    NSError,
    NSNumber,
    NSObject,
    NSString,
)
from ..libdispatch import dispatch_queue_t

class CBManager(NSObject):
    def state(self) -> CBManagerState: ...

TCBCentralManager = TypeVar("TCBCentralManager", bound=CBCentralManager)

class CBCentralManager(CBManager):
    @classmethod
    def init(cls: Type[TCBCentralManager]) -> Optional[TCBCentralManager]: ...
    @classmethod
    def initWithDelegate_queue_(
        cls: Type[TCBCentralManager],
        delegate: CBCentralManagerDelegate,
        queue: dispatch_queue_t,
    ) -> Optional[TCBCentralManager]: ...
    @classmethod
    def initWithDelegate_queue_options_(
        cls: Type[TCBCentralManager],
        delegate: CBCentralManagerDelegate,
        queue: dispatch_queue_t,
        options: NSDictionary,
    ) -> Optional[TCBCentralManager]: ...
    def connectPeripheral_options_(
        self, peripheral: CBPeripheral, options: Optional[NSDictionary]
    ) -> None: ...
    def cancelPeripheralConnection_(self, peripheral: CBPeripheral) -> None: ...
    def retrieveConnectedPeripheralsWithServices_(
        self, serviceUUIDs: NSArray
    ) -> NSArray: ...
    def retrievePeripheralsWithIdentifiers_(self, serviceUUIDs: NSArray) -> NSArray: ...
    def scanForPeripheralsWithServices_options_(
        self, serviceUUIDs: Optional[NSArray], options: Optional[NSDictionary]
    ) -> None: ...
    def stopScan(self) -> None: ...
    def isScanning(self) -> bool: ...
    @classmethod
    def supportsFeatures(cls, features: CBCentralManagerFeature) -> bool: ...
    def delegate(self) -> Optional[CBCentralManagerDelegate]: ...
    def registerForConnectionEventsWithOptions_(
        self, options: NSDictionary
    ) -> None: ...

CBConnectPeripheralOptionNotifyOnConnectionKey: NSString
CBConnectPeripheralOptionNotifyOnDisconnectionKey: NSString
CBConnectPeripheralOptionNotifyOnNotificationKey: NSString
CBConnectPeripheralOptionEnableTransportBridgingKey: NSString
CBConnectPeripheralOptionRequiresANCS: NSString
CBConnectPeripheralOptionStartDelayKey: NSString

CBCentralManagerScanOptionAllowDuplicatesKey: NSString
CBCentralManagerScanOptionSolicitedServiceUUIDsKey: NSString

CBCentralManagerFeature = NewType("CBCentralManagerFeature", int)

CBCentralManagerFeatureExtendedScanAndConnect: CBCentralManagerFeature

CBManagerState = NewType("CBManagerState", int)

CBManagerStatePoweredOff: CBManagerState
CBManagerStatePoweredOn: CBManagerState
CBManagerStateResetting: CBManagerState
CBManagerStateUnauthorized: CBManagerState
CBManagerStateUnknown: CBManagerState
CBManagerStateUnsupported: CBManagerState

CBConnectionEvent = NewType("CBConnectionEvent", int)

CBConnectionEventPeerConnected: CBConnectionEvent
CBConnectionEventPeerDisconnected: CBConnectionEvent

class CBConnectionEventMatchingOption(NSString): ...

CBConnectionEventMatchingOptionPeripheralUUIDs: CBConnectionEventMatchingOption
CBConnectionEventMatchingOptionServiceUUIDs: CBConnectionEventMatchingOption

class CBCentralManagerDelegate: ...

class CBPeer(NSObject):
    def identifier(self) -> NSUUID: ...

class CBPeripheral(CBPeer):
    def name(self) -> NSString: ...
    def delegate(self) -> CBPeripheralDelegate: ...
    def discoverServices_(self, serviceUUIDs: NSArray) -> None: ...
    def discoverIncludedServices_forService_(
        self, includedServiceUUIDs: NSArray, service: CBService
    ) -> None: ...
    def services(self) -> NSArray: ...
    def discoverCharacteristics_forService_(
        self, characteristicUUIDs: NSArray, service: CBService
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
    ) -> None: ...
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

class CBPeripheralDelegate:
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
    def pperipheralIsReadyToSendWriteWithoutResponse_(
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
        RSSI: NSNumber,
        error: Optional[NSError],
    ) -> None: ...
    def peripheralDidUpdateName_(self, peripheral: CBPeripheral) -> None: ...
    def peripheral_didModifyServices_(
        self, peripheral: CBPeripheral, invalidatedServices: NSArray
    ) -> None: ...

class CBAttribute(NSObject):
    def UUID(self) -> CBUUID: ...

class CBService(CBAttribute):
    def peripheral(self) -> CBPeripheral: ...
    def isPrimary(self) -> bool: ...
    def characteristics(self) -> Optional[NSArray]: ...
    def includedServices(self) -> Optional[NSArray]: ...

class CBUUID(NSObject):
    @classmethod
    def UUIDWithString_(cls, theString: NSString) -> CBUUID: ...
    @classmethod
    def UUIDWithData_(cls, theData: NSData) -> CBUUID: ...
    @classmethod
    def UUIDWithNSUUID_(cls, theUUID: NSUUID) -> CBUUID: ...
    def data(self) -> NSData: ...
    def UUIDString(self) -> NSString: ...

class CBCharacteristic(CBAttribute):
    def service(self) -> CBService: ...
    def value(self) -> Optional[NSData]: ...
    def descriptors(self) -> Optional[NSArray]: ...
    def properties(self) -> CBCharacteristicProperties: ...
    def isNotifying(self) -> bool: ...

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
