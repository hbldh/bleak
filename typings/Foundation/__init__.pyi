from collections.abc import Sequence
from typing import NewType, Optional, TypeVar

TNSObject = TypeVar("TNSObject", bound=NSObject)

class NSObject:
    @classmethod
    def alloc(cls: type[TNSObject]) -> TNSObject: ...
    def init(self: TNSObject) -> Optional[TNSObject]: ...
    def addObserver_forKeyPath_options_context_(
        self,
        observer: NSObject,
        keyPath: NSString,
        options: NSKeyValueObservingOptions,
        context: int,
    ) -> None: ...
    def removeObserver_forKeyPath_(
        self, observer: NSObject, keyPath: NSString
    ) -> None: ...

class NSDictionary(NSObject): ...
class NSUUID(NSObject): ...
class NSString(NSObject): ...
class NSError(NSObject): ...
class NSData(NSObject): ...

class NSArray(NSObject):
    def initWithArray_(self, array: Sequence) -> NSArray: ...

class NSValue(NSObject): ...
class NSNumber(NSValue): ...

NSKeyValueObservingOptions = NewType("NSKeyValueObservingOptions", int)
NSKeyValueObservingOptionNew: NSKeyValueObservingOptions
NSKeyValueObservingOptionOld: NSKeyValueObservingOptions
NSKeyValueObservingOptionInitial: NSKeyValueObservingOptions
NSKeyValueObservingOptionPrior: NSKeyValueObservingOptions

NSKeyValueChangeKey = NewType("NSKeyValueChangeKey", NSString)
NSKeyValueChangeIndexesKey: NSKeyValueChangeKey
NSKeyValueChangeKindKey: NSKeyValueChangeKey
NSKeyValueChangeNewKey: NSKeyValueChangeKey
NSKeyValueChangeNotificationIsPriorKey: NSKeyValueChangeKey
NSKeyValueChangeOldKey: NSKeyValueChangeKey
