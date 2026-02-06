from typing import Any, NewType

from rubicon.objc.api import NSKeyValueObservingOptions, NSObject, NSString

class NSProcessInfo(NSObject):
    processInfo: "NSProcessInfo"

    @property
    def operatingSystemVersion(self) -> Any: ...

class NSUUID(NSObject):
    @classmethod
    def UUIDWithString_(cls, uuidString: str) -> NSUUID: ...
    @property
    def UUIDString(self) -> NSString: ...
    def isEqualToUUID_(self, other: NSUUID) -> bool: ...

class NSBundle(NSObject):
    mainBundle: NSBundle
    @property
    def bundleIdentifier(self) -> NSString: ...

NSErrorDomain = NewType("NSErrorDomain", NSString)

class NSError(NSObject):
    @property
    def domain(self) -> NSErrorDomain: ...
    @property
    def code(self) -> int: ...

NSKeyValueChangeKey = NewType("NSKeyValueChangeKey", str)
NSKeyValueChangeIndexesKey: NSKeyValueChangeKey
NSKeyValueChangeKindKey: NSKeyValueChangeKey
NSKeyValueChangeNewKey: NSKeyValueChangeKey
NSKeyValueChangeNotificationIsPriorKey: NSKeyValueChangeKey
NSKeyValueChangeOldKey: NSKeyValueChangeKey

NSKeyValueObservingOptionNew: NSKeyValueObservingOptions
NSKeyValueObservingOptionOld: NSKeyValueObservingOptions
NSKeyValueObservingOptionInitial: NSKeyValueObservingOptions
NSKeyValueObservingOptionPrior: NSKeyValueObservingOptions
