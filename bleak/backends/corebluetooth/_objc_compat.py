import enum
import os
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"


class ObjcFramework(str, enum.Enum):
    """Identifiers for Objective-C frameworks used by Bleak CoreBluetooth backend.

    .. versionadded:: unreleased
    """

    PYOBJC = "pyobjc"
    """
    PyObjC framework.
    """

    RUBICON_OBJC = "rubicon-objc"
    """
    Rubicon-ObjC framework.
    """


def get_objc_framework() -> ObjcFramework:
    return ObjcFramework(os.environ.get("BLEAK_COREBLUETOOTH_FRAMEWORK", "pyobjc"))


BLEAK_OBJC_FRAMEWORK_IS_PYOBJC = get_objc_framework() == ObjcFramework.PYOBJC
BLEAK_OBJC_FRAMEWORK_IS_RUBICON = get_objc_framework() == ObjcFramework.RUBICON_OBJC


# Import ObjC classes
#     1. In `pyobjc` it is possible to uses the python import system:
#           `from CoreBluetooth import CBCentralManager`
#
#     2. In `rubicon-objc` you have to create these objects explictly:
#           `CBCentralManager = ObjCClass("CBCentralManager“)`
#
#  => Import the ObjC classes from this file. All classes that are used are defined
#     here for both frameworks and uses the correct one. For example:
#           `from bleak.backends.corebluetooth._objc_compat import CBCentralManager`
if BLEAK_OBJC_FRAMEWORK_IS_PYOBJC:
    import objc
    from CoreBluetooth import CBUUID as CBUUID
    from CoreBluetooth import CBATTErrorDomain as CBATTErrorDomain
    from CoreBluetooth import CBCentralManager as CBCentralManager
    from CoreBluetooth import CBCharacteristic as CBCharacteristic
    from CoreBluetooth import CBCharacteristicWriteType as CBCharacteristicWriteType
    from CoreBluetooth import (
        CBCharacteristicWriteWithoutResponse as CBCharacteristicWriteWithoutResponse,
    )
    from CoreBluetooth import (
        CBCharacteristicWriteWithResponse as CBCharacteristicWriteWithResponse,
    )
    from CoreBluetooth import CBDescriptor as CBDescriptor
    from CoreBluetooth import (
        CBManagerAuthorizationDenied as CBManagerAuthorizationDenied,
    )
    from CoreBluetooth import (
        CBManagerAuthorizationRestricted as CBManagerAuthorizationRestricted,
    )
    from CoreBluetooth import CBManagerState as CBManagerState
    from CoreBluetooth import CBManagerStatePoweredOff as CBManagerStatePoweredOff
    from CoreBluetooth import CBManagerStatePoweredOn as CBManagerStatePoweredOn
    from CoreBluetooth import CBManagerStateResetting as CBManagerStateResetting
    from CoreBluetooth import CBManagerStateUnauthorized as CBManagerStateUnauthorized
    from CoreBluetooth import CBManagerStateUnknown as CBManagerStateUnknown
    from CoreBluetooth import CBManagerStateUnsupported as CBManagerStateUnsupported
    from CoreBluetooth import CBPeripheral as CBPeripheral
    from CoreBluetooth import CBPeripheralStateConnected as CBPeripheralStateConnected
    from CoreBluetooth import CBService as CBService
    from CoreBluetooth import (
        CBUUIDCharacteristicExtendedPropertiesString as CBUUIDCharacteristicExtendedPropertiesString,
    )
    from CoreBluetooth import (
        CBUUIDCharacteristicUserDescriptionString as CBUUIDCharacteristicUserDescriptionString,
    )
    from CoreBluetooth import (
        CBUUIDClientCharacteristicConfigurationString as CBUUIDClientCharacteristicConfigurationString,
    )
    from CoreBluetooth import (
        CBUUIDServerCharacteristicConfigurationString as CBUUIDServerCharacteristicConfigurationString,
    )
    from Foundation import NSUUID as NSUUID
    from Foundation import NSArray as NSArray
    from Foundation import NSBundle as NSBundle
    from Foundation import NSData as NSData
    from Foundation import NSDictionary as NSDictionary
    from Foundation import NSError as NSError
    from Foundation import NSKeyValueChangeNewKey as NSKeyValueChangeNewKey
    from Foundation import NSKeyValueObservingOptionNew as NSKeyValueObservingOptionNew
    from Foundation import NSNumber as NSNumber
    from Foundation import NSObject as NSObject
    from Foundation import NSString as NSString
    from libdispatch import DISPATCH_QUEUE_SERIAL as DISPATCH_QUEUE_SERIAL
    from libdispatch import dispatch_queue_create as dispatch_queue_create
    from objc import macos_available as macos_available

    CBCentralManagerDelegate = objc.protocolNamed("CBCentralManagerDelegate")
    CBPeripheralDelegate = objc.protocolNamed("CBPeripheralDelegate")

    objc.options.verbose = True

elif BLEAK_OBJC_FRAMEWORK_IS_RUBICON:
    from rubicon.objc.api import NSArray as NSArray
    from rubicon.objc.api import NSData as NSData
    from rubicon.objc.api import NSDictionary as NSDictionary
    from rubicon.objc.api import NSNumber as NSNumber
    from rubicon.objc.api import NSObject as NSObject
    from rubicon.objc.api import NSString as NSString
    from rubicon.objc.api import py_from_ns

    from ._rubicon_objc import macos_available as macos_available
    from ._rubicon_objc.CoreBluetooth import CBUUID as CBUUID
    from ._rubicon_objc.CoreBluetooth import CBATTErrorDomain as CBATTErrorDomain
    from ._rubicon_objc.CoreBluetooth import CBCentralManager as CBCentralManager
    from ._rubicon_objc.CoreBluetooth import (
        CBCentralManagerDelegate as CBCentralManagerDelegate,
    )
    from ._rubicon_objc.CoreBluetooth import CBCharacteristic as CBCharacteristic
    from ._rubicon_objc.CoreBluetooth import (
        CBCharacteristicWriteType as CBCharacteristicWriteType,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBCharacteristicWriteWithoutResponse as CBCharacteristicWriteWithoutResponse,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBCharacteristicWriteWithResponse as CBCharacteristicWriteWithResponse,
    )
    from ._rubicon_objc.CoreBluetooth import CBDescriptor as CBDescriptor
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerAuthorizationDenied as CBManagerAuthorizationDenied,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerAuthorizationRestricted as CBManagerAuthorizationRestricted,
    )
    from ._rubicon_objc.CoreBluetooth import CBManagerState as CBManagerState
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerStatePoweredOff as CBManagerStatePoweredOff,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerStatePoweredOn as CBManagerStatePoweredOn,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerStateResetting as CBManagerStateResetting,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerStateUnauthorized as CBManagerStateUnauthorized,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerStateUnknown as CBManagerStateUnknown,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBManagerStateUnsupported as CBManagerStateUnsupported,
    )
    from ._rubicon_objc.CoreBluetooth import CBPeripheral as CBPeripheral
    from ._rubicon_objc.CoreBluetooth import (
        CBPeripheralDelegate as CBPeripheralDelegate,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBPeripheralStateConnected as CBPeripheralStateConnected,
    )
    from ._rubicon_objc.CoreBluetooth import CBService as CBService
    from ._rubicon_objc.CoreBluetooth import (
        CBUUIDCharacteristicExtendedPropertiesString as CBUUIDCharacteristicExtendedPropertiesString,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBUUIDCharacteristicUserDescriptionString as CBUUIDCharacteristicUserDescriptionString,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBUUIDClientCharacteristicConfigurationString as CBUUIDClientCharacteristicConfigurationString,
    )
    from ._rubicon_objc.CoreBluetooth import (
        CBUUIDServerCharacteristicConfigurationString as CBUUIDServerCharacteristicConfigurationString,
    )
    from ._rubicon_objc.Foundation import NSUUID as NSUUID
    from ._rubicon_objc.Foundation import NSBundle as NSBundle
    from ._rubicon_objc.Foundation import NSError as NSError
    from ._rubicon_objc.Foundation import (
        NSKeyValueChangeNewKey as NSKeyValueChangeNewKey,
    )
    from ._rubicon_objc.Foundation import (
        NSKeyValueObservingOptionNew as NSKeyValueObservingOptionNew,
    )
    from ._rubicon_objc.libdispatch import (
        DISPATCH_QUEUE_SERIAL as DISPATCH_QUEUE_SERIAL,
    )
    from ._rubicon_objc.libdispatch import (
        dispatch_queue_create as dispatch_queue_create,
    )


# Converting basic ObjC types to python types:
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
if BLEAK_OBJC_FRAMEWORK_IS_PYOBJC:

    def to_int(objc_obj: NSNumber) -> int:
        """Converts an NSNumber to a Python int."""
        return int(objc_obj)

    def to_str(objc_obj: NSString) -> str:
        """Converts an NSString to a Python string."""
        return str(objc_obj)

    def to_bytes(objc_obj: NSData) -> bytes:
        """Converts an NSData to a Python bytes."""
        return bytes(objc_obj)

elif BLEAK_OBJC_FRAMEWORK_IS_RUBICON:

    def to_int(objc_obj: NSNumber) -> int:
        """Converts an NSNumber to a Python int."""
        ret = py_from_ns(objc_obj)
        if not isinstance(ret, int):
            raise TypeError(f"Expected int, got {type(ret)}")
        return ret

    def to_str(objc_obj: NSString) -> str:
        """Converts an NSString to a Python string."""
        return py_from_ns(objc_obj)

    def to_bytes(objc_obj: NSData) -> bytes:
        """Converts an NSData to a Python bytes."""
        return py_from_ns(objc_obj)


T = TypeVar("T")


# Access to Objc object properties:
#     1. In `pyobjc` object properties are accessed via function calls:
#           `state = central_manager.state()`
#
#     2. In `rubicon-objc` object properties are accessed like python properties:
#            `state = central_manager.state`
#
#  => Use `get_prop` to access properties:
#            `state = get_prop(central_manager.state)`
if BLEAK_OBJC_FRAMEWORK_IS_PYOBJC:

    def get_prop(prop: Callable[[], T]) -> T:
        """Get a property from an Objective-C object."""
        return prop()

elif BLEAK_OBJC_FRAMEWORK_IS_RUBICON:

    def get_prop(prop: T) -> T:
        """Get a property from an Objective-C object."""
        return prop


# Adding objc/python methods to delegates:
#     1. In `pyobjc` when inherit from `NSObject` every method is an objc method, except
#        you add `@objc.python_method` to define python methods.
#
#     2. In `rubicon-objc` when inherit from `NSObject` you have to declare objc-methods
#        with `@objc_method`. Adding an normal python methods is possible, but it is
#        not possible to call them.
#
#  => Use the following new decorator `@objc_method` on all objc methods and remove python
#     methods completly from your ObjC classes.
if BLEAK_OBJC_FRAMEWORK_IS_PYOBJC:

    def objc_method(func: T) -> T:
        """Decorator for Objective-C methods."""
        return func

elif BLEAK_OBJC_FRAMEWORK_IS_RUBICON:
    from typing import no_type_check

    from rubicon.objc.api import objc_method as _objc_method

    F = TypeVar("F", bound=Callable[..., Any])

    def objc_method(func: F) -> F:
        """Decorator for Objective-C methods."""
        # Normally rubicon-objc parses the type hints from `func` for e.g. ctypes types, but the type hints
        # we use are not compatible. So we remove all type hints with `no_type_check` before passing the
        # function to rubicon-objc.
        return cast(F, _objc_method(no_type_check(func)))


# Passing python objects to objc delegate constructor:
#     1. In `pyobjc` you can pass every python object in the constructor without problem.
#
#     2. In `rubicon-objc` it is not possible to pass python objects into the constructor.
#        But it is possible to create an objc property via `rubicon.api.objc_property` that
#        holds a python object. Then after object creation you can assign the python object
#        to that property.
#
#  => Do not pass python objects to ObjC methods. Instead create an ObjC property via
#     `objc_py_property` and assign the python object after creation to that property.
if BLEAK_OBJC_FRAMEWORK_IS_PYOBJC:

    def objc_py_property() -> Any:
        """Objective-C property of a python object."""
        return None

elif BLEAK_OBJC_FRAMEWORK_IS_RUBICON:
    from rubicon.objc.api import objc_property as _objc_property

    def objc_py_property() -> Any:
        """Objective-C property of a python object."""
        return _objc_property(object)
