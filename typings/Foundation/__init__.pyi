import sys
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Callable, NewType, Optional, TypeVar, Union, overload

if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

Property = Union[
    Callable[[], T],  # "pyobjc" style
    T,  # "rubicon-objc" style
]

TNSObject = TypeVar("TNSObject", bound=NSObject)

class NSObject:
    @classmethod
    def alloc(cls) -> Self: ...
    def init(self) -> Optional[Self]: ...
    def addObserver_forKeyPath_options_context_(
        self,
        observer: NSObject,
        keyPath: str,
        options: NSKeyValueObservingOptions,
        context: int,
    ) -> None: ...
    def removeObserver_forKeyPath_(self, observer: NSObject, keyPath: str) -> None: ...
    @classmethod
    def __init_subclass__(cls, /, protocols: Sequence[Any] = []) -> None: ...

K = TypeVar("K")
V = TypeVar("V")

class NSDictionary(NSObject, Mapping[K, V]):
    def __getitem__(self, key: K) -> V: ...
    def __iter__(self) -> Iterator[K]: ...
    def __len__(self) -> int: ...

class NSUUID(NSObject):
    @classmethod
    def UUIDWithString_(cls, uuidString: str) -> NSUUID: ...
    def UUIDString(self) -> NSString: ...
    def isEqualToUUID_(self, other: NSUUID) -> bool: ...

class NSError(NSObject): ...

class NSData(NSObject, Buffer):
    def initWithBytes_length_(self, bytes: Buffer, length: int) -> Self: ...
    def length(self) -> int: ...
    def getBytes_length_(self, buffer: bytes, length: int) -> None: ...

T = TypeVar("T")

class NSArray(NSObject, Sequence[T]):
    @overload
    def __getitem__(self, index: int) -> T: ...
    @overload
    def __getitem__(self, index: slice) -> Sequence[T]: ...
    def __len__(self) -> int: ...
    def initWithArray_(self, array: Sequence[Any]) -> Self: ...

class NSValue(NSObject): ...
class NSNumber(NSObject): ...
class NSString(NSObject): ...

class NSBundle(NSObject):
    @property
    @classmethod
    def mainBundle(cls) -> Property[NSBundle]: ...  # type: ignore
    bundleIdentifier: Property[NSString]

NSKeyValueObservingOptions = NewType("NSKeyValueObservingOptions", int)
NSKeyValueObservingOptionNew: NSKeyValueObservingOptions
NSKeyValueObservingOptionOld: NSKeyValueObservingOptions
NSKeyValueObservingOptionInitial: NSKeyValueObservingOptions
NSKeyValueObservingOptionPrior: NSKeyValueObservingOptions

NSKeyValueChangeKey = NewType("NSKeyValueChangeKey", str)
NSKeyValueChangeIndexesKey: NSKeyValueChangeKey
NSKeyValueChangeKindKey: NSKeyValueChangeKey
NSKeyValueChangeNewKey: NSKeyValueChangeKey
NSKeyValueChangeNotificationIsPriorKey: NSKeyValueChangeKey
NSKeyValueChangeOldKey: NSKeyValueChangeKey
