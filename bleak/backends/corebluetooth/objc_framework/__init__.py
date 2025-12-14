# This file is used as an abstraction level to support `pyobjc` and `rubicon-objc`
#
# There are some notable differences between `pyobjc` and `rubicon-objc`:
#
# 1. Import objc classes
#     1. In `pyobjc` it is possible to uses the python import system:
#           `from CoreBluetooth import CBCentralManager`
#
#     2. In `rubicon-objc` you have to create these objects explictly:
#           `CBCentralManager = ObjCClass("CBCentralManager“)`
#
#  => Import the objc classes from `from bleak.backends.corebluetooth.objc_framework`.
#     All classes that are used are defined here for both frameworks and uses the
#     correct one. For example:
#           `from bleak.backends.corebluetooth.objc_framework import CBCentralManager`
#
#
# 2. Converting basic objc types to python types:
#     1. In `pyobjc` the base class for `NSNumber` and `NSString` are subtype of similar
#        python types (but not all of them like `NSData`). For example:
#          - `isinstance(NSNumber.numberWithInt_(42), int)    == True`
#          - `isinstance(NSString.stringWithString_(""), str) == True`
#          - `isinstance(NSData.alloc().init(), bytes)        == False`
#
#     2. In `rubicon-objc` no automatic conversion is done:
#          - `isinstance(NSNumber.numberWithInt_(42), int)    == False`
#          - `isinstance(NSString.stringWithString_(""), str) == False`
#          - `isinstance(NSData.alloc().init(), bytes)        == False`
#        You have to convert all objc objects explicitly to python types via `py_from_ns`.
#
#  => These objc types have to be converted to python types via `to_int`, `to_str` and
#     `to_bytes`.
#
#
# 3. Access to Objc object properties:
#     1. In `pyobjc` object properties are accessed via function calls:
#           `state = central_manager.state()`
#
#     2. In `rubicon-objc` object properties are accessed like python properties:
#            `state = central_manager.state`
#
#  => Use `get_prop` to access properties:
#           `state = get_prop(central_manager.state)`
#
#
# 4. Adding objc/python methods to delegates:
#     1. In `pyobjc` when inherit from `NSObject` every method is an objc method, except
#        you add `@objc.python_method` to define python methods.
#
#     2. In `rubicon-objc` when inherit from `NSObject` you have to declare objc-methods
#        with `@objc_method`. Adding an normal python methods is possible, but it is
#        not possible to call them.
#
#  => A new decorator `@objc_method` is defined for both frameworks as abstraction.
#     Defining python methods is completly removed.
#
#
# 5. Type hints of `@objc_method`
#     1. In `pyojc` it is possible to add type hints to methods decorated with
#        `@objc_method`.
#
#     2. In `rubicon-objc` the type hints are parsed by `rubicon-objc`. Only special
#        values can be used. Mostly the type hint has to be skipped.
#
#  => A workaround is to use „# type:“ comments instead of actual type hints. Tools
#     like pylance understands that too, but as these are comments they are not available
#     at runtime.
#
#
# 6. Passing python objects to objc delegate constructor:
#     1. In `pyobjc` you can pass every python object in the constructor without problem.
#
#     2. In `rubicon-objc` it is not possible to pass python objects into the constructor.
#        But after class creation it is possible to add objects dynamically to the object,
#        that is accessible from the objc methods.
#
#  => Do not pass python objects to objc delegates. That is the only working approach for
#     `rubicon-objc` and also working for `pyobjc`.
#


import os
import sys
from typing import TYPE_CHECKING

from bleak.exc import BleakError

if sys.platform == "darwin":
    FRAMEWORK = os.environ.get("BLEAK_COREBLUETOOTH_FRAMEWORK", "pyobjc")
elif sys.platform == "ios":
    FRAMEWORK = "rubicon-objc"
else:
    raise BleakError(f"Unsupported sys.platform '{sys.platform}'")

if TYPE_CHECKING or FRAMEWORK == "pyobjc":
    from bleak.backends.corebluetooth.objc_framework.pyobjc import (
        CBUUID,
        DISPATCH_QUEUE_SERIAL,
        NSUUID,
        CBCentralManager,
        CBCentralManagerDelegate,
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
        CBPeripheralDelegate,
        CBPeripheralState,
        CBPeripheralStateConnected,
        CBPeripheralStateConnecting,
        CBPeripheralStateDisconnected,
        CBPeripheralStateDisconnecting,
        CBService,
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
        dispatch_queue_create,
        get_prop,
        macos_available,
        objc_method,
        to_bytes,
        to_int,
        to_str,
    )

elif FRAMEWORK == "rubicon-objc":
    from bleak.backends.corebluetooth.objc_framework.rubicon_objc import (
        CBUUID,
        DISPATCH_QUEUE_SERIAL,
        NSUUID,
        CBCentralManager,
        CBCentralManagerDelegate,
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
        CBPeripheralDelegate,
        CBPeripheralState,
        CBPeripheralStateConnected,
        CBPeripheralStateConnecting,
        CBPeripheralStateDisconnected,
        CBPeripheralStateDisconnecting,
        CBService,
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
        dispatch_queue_create,
        get_prop,
        macos_available,
        objc_method,
        to_bytes,
        to_int,
        to_str,
    )
else:
    raise BleakError(f"Unsupported CoreBluetooth framework '{FRAMEWORK}'")


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
