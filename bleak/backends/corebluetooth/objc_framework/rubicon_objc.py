import ctypes
from typing import Any, Callable, TypeVar

from rubicon.objc import (
    ObjCClass,
    ObjCInstance,
    ObjCProtocol,
    objc_const,
    objc_method,
    py_from_ns,
)
from rubicon.objc.api import (
    NSArray,
    NSData,
    NSDictionary,
    NSNumber,
    NSObject,
    NSString,
)
from rubicon.objc.runtime import Foundation, load_library, objc_id

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

NSUUID = ObjCClass("NSUUID")
NSError = ObjCClass("NSError")
NSBundle = ObjCClass("NSBundle")

NSKeyValueObservingOptions = int
NSKeyValueObservingOptionNew = 0x01
NSKeyValueObservingOptionOld = 0x02
NSKeyValueObservingOptionInitial = 0x04
NSKeyValueObservingOptionPrior = 0x08


NSKeyValueChangeKey = str
NSKeyValueChangeIndexesKey = objc_const(Foundation, "NSKeyValueChangeIndexesKey")
NSKeyValueChangeKindKey = objc_const(Foundation, "NSKeyValueChangeKindKey")
NSKeyValueChangeNewKey = objc_const(Foundation, "NSKeyValueChangeNewKey")
NSKeyValueChangeNotificationIsPriorKey = objc_const(
    Foundation, "NSKeyValueChangeNotificationIsPriorKey"
)
NSKeyValueChangeOldKey = objc_const(Foundation, "NSKeyValueChangeOldKey")


T = TypeVar("T")


def get_prop(prop: T | Callable[[], T]) -> T:
    return py_from_ns(prop)


def to_int(objc_obj: NSNumber) -> int:
    return py_from_ns(objc_obj)


def to_str(objc_obj: NSString) -> str:
    return py_from_ns(objc_obj)


def to_bytes(objc_obj: NSData) -> bytes:
    return py_from_ns(objc_obj)


# On Mac and iOS, libdispatch is part of libSystem.
libSystem = load_library("System")
libdispatch = libSystem

dispatch_queue_t = ctypes.c_void_p
dispatch_queue_attr_t = ctypes.c_void_p

libdispatch.dispatch_queue_create.argtypes = [ctypes.c_char_p, dispatch_queue_attr_t]
libdispatch.dispatch_queue_create.restype = dispatch_queue_t


DISPATCH_QUEUE_SERIAL: dispatch_queue_attr_t = dispatch_queue_attr_t(None)


def dispatch_queue_create(label: bytes, attr: dispatch_queue_attr_t):
    queue = libdispatch.dispatch_queue_create(label, attr)
    return ObjCInstance(ctypes.cast(queue, objc_id))  # type: ignore


def macos_available(major: int, minor: int, patch: int = 0) -> bool:
    NSProcessInfo = ObjCClass("NSProcessInfo")
    version = NSProcessInfo.processInfo.operatingSystemVersion

    current = (version.field_0, version.field_1, version.field_2)
    required = (major, minor, patch)

    return current >= required


__all__ = [
    "CBUUID",
    "DISPATCH_QUEUE_SERIAL",
    "NSUUID",
    "CBCentralManager",
    "CBCentralManagerDelegate",
    "CBCharacteristic",
    "CBCharacteristicWriteType",
    "CBCharacteristicWriteWithoutResponse",
    "CBCharacteristicWriteWithResponse",
    "CBDescriptor",
    "CBManagerAuthorizationAllowedAlways",
    "CBManagerAuthorizationDenied",
    "CBManagerAuthorizationNotDetermined",
    "CBManagerAuthorizationRestricted",
    "CBManagerStatePoweredOff",
    "CBManagerStatePoweredOn",
    "CBManagerStateResetting",
    "CBManagerStateUnauthorized",
    "CBManagerStateUnknown",
    "CBManagerStateUnsupported",
    "CBPeripheral",
    "CBPeripheralDelegate",
    "CBPeripheralState",
    "CBPeripheralStateConnected",
    "CBPeripheralStateConnecting",
    "CBPeripheralStateDisconnected",
    "CBPeripheralStateDisconnecting",
    "CBService",
    "NSArray",
    "NSBundle",
    "NSData",
    "NSDictionary",
    "NSError",
    "NSKeyValueChangeNewKey",
    "NSKeyValueObservingOptionNew",
    "NSNumber",
    "NSObject",
    "NSString",
    "dispatch_queue_create",
    "get_prop",
    "macos_available",
    "objc_method",
    "to_int",
    "to_str",
    "to_bytes",
]
