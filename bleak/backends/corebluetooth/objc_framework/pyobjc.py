import typing
from collections.abc import Callable
from typing import Any, TypeVar

import objc
from CoreBluetooth import (
    CBUUID,
    CBCentralManager,
    CBCharacteristic,
    CBCharacteristicWriteType,
    CBCharacteristicWriteWithoutResponse,
    CBCharacteristicWriteWithResponse,
    CBDescriptor,
    CBManagerAuthorizationAllowedAlways,
    CBManagerAuthorizationDenied,
    CBManagerAuthorizationNotDetermined,
    CBManagerAuthorizationRestricted,
    CBManagerStatePoweredOff,
    CBManagerStatePoweredOn,
    CBManagerStateResetting,
    CBManagerStateUnauthorized,
    CBManagerStateUnknown,
    CBManagerStateUnsupported,
    CBPeripheral,
    CBPeripheralState,
    CBPeripheralStateConnected,
    CBPeripheralStateConnecting,
    CBPeripheralStateDisconnected,
    CBPeripheralStateDisconnecting,
    CBService,
)
from Foundation import (
    NSUUID,
    NSArray,
    NSBundle,
    NSData,
    NSDictionary,
    NSError,
    NSKeyValueChangeNewKey,
    NSKeyValueObservingOptionNew,
    NSNumber,
    NSObject,
    NSString,
)
from libdispatch import (
    DISPATCH_QUEUE_SERIAL,
    dispatch_queue_create,
)
from objc import macos_available

objc.options.verbose = True


CBCentralManagerDelegate = objc.protocolNamed("CBCentralManagerDelegate")
CBPeripheralDelegate = objc.protocolNamed("CBPeripheralDelegate")


T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def get_prop(prop: T | Callable[[], T]) -> T:
    return prop()


def to_int(objc_obj: NSNumber) -> int:
    return int(objc_obj)  # type: ignore


def to_str(objc_obj: NSString) -> str:
    return str(objc_obj)  # type: ignore


def to_bytes(objc_obj: NSData) -> bytes:
    return bytes(objc_obj)  # type: ignore


def objc_method(func: T) -> T:
    return func


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
