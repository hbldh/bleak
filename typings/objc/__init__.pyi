from typing import Literal, Optional, TypeVar, overload

from CoreBluetooth import CBCentralManagerDelegate, CBPeripheralDelegate
from Foundation import NSObject

T = TypeVar("T")

class _OptionsType:
    deprecation_warnings: bool
    structs_indexable: bool
    structs_writable: bool
    unknown_pointer_raises: bool
    use_kvo: bool
    verbose: bool

options: _OptionsType

def super(cls: type, self: T) -> T: ...
def macos_available(major: int, minor: int, patch: int = 0) -> bool: ...
def python_method(func: T) -> T: ...

class pyobjc_unicode(str): ...

class WeakRef:
    def __init__(self, object: NSObject) -> None: ...
    def __call__(self) -> Optional[NSObject]: ...

@overload
def protocolNamed(
    name: Literal["CBCentralManagerDelegate"],
) -> type[CBCentralManagerDelegate]: ...
@overload
def protocolNamed(
    name: Literal["CBPeripheralDelegate"],
) -> type[CBPeripheralDelegate]: ...
