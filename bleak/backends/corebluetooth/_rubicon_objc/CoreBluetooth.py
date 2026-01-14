from rubicon.objc import ObjCClass, ObjCProtocol
from rubicon.objc.api import objc_const
from rubicon.objc.runtime import load_library

CoreBluetooth = load_library("CoreBluetooth")

CBUUID = ObjCClass("CBUUID")
CBCentralManager = ObjCClass("CBCentralManager")
CBCentralManagerDelegate = ObjCProtocol("CBCentralManagerDelegate")
CBCharacteristic = ObjCClass("CBCharacteristic")
CBDescriptor = ObjCClass("CBDescriptor")
CBPeripheral = ObjCClass("CBPeripheral")
CBPeripheralDelegate = ObjCProtocol("CBPeripheralDelegate")
CBService = ObjCClass("CBService")

CBManagerState = int
CBManagerStateUnknown = 0
CBManagerStateResetting = 1
CBManagerStateUnsupported = 2
CBManagerStateUnauthorized = 3
CBManagerStatePoweredOff = 4
CBManagerStatePoweredOn = 5


CBManagerAuthorization = int
CBManagerAuthorizationNotDetermined = 0
CBManagerAuthorizationRestricted = 1
CBManagerAuthorizationDenied = 2
CBManagerAuthorizationAllowedAlways = 3


CBCharacteristicWriteType = int
CBCharacteristicWriteWithResponse = 0
CBCharacteristicWriteWithoutResponse = 1


CBPeripheralState = int
CBPeripheralStateDisconnected = 0
CBPeripheralStateConnecting = 1
CBPeripheralStateConnected = 2
CBPeripheralStateDisconnecting = 3

CBATTErrorDomain = objc_const(CoreBluetooth, "CBATTErrorDomain")
CBErrorDomain = objc_const(CoreBluetooth, "CBErrorDomain")

CBUUIDCharacteristicExtendedPropertiesString = objc_const(
    CoreBluetooth, "CBUUIDCharacteristicExtendedPropertiesString"
)
CBUUIDCharacteristicUserDescriptionString = objc_const(
    CoreBluetooth, "CBUUIDCharacteristicUserDescriptionString"
)
CBUUIDClientCharacteristicConfigurationString = objc_const(
    CoreBluetooth, "CBUUIDClientCharacteristicConfigurationString"
)
CBUUIDServerCharacteristicConfigurationString = objc_const(
    CoreBluetooth, "CBUUIDServerCharacteristicConfigurationString"
)
CBUUIDCharacteristicFormatString = objc_const(
    CoreBluetooth, "CBUUIDCharacteristicFormatString"
)
CBUUIDCharacteristicAggregateFormatString = objc_const(
    CoreBluetooth, "CBUUIDCharacteristicAggregateFormatString"
)
CBUUIDL2CAPPSMCharacteristicString = objc_const(
    CoreBluetooth, "CBUUIDL2CAPPSMCharacteristicString"
)
