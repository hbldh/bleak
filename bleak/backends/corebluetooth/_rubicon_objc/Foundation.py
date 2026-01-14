from rubicon.objc import ObjCClass
from rubicon.objc.api import objc_const
from rubicon.objc.runtime import Foundation

NSUUID = ObjCClass("NSUUID")
NSBundle = ObjCClass("NSBundle")
NSError = ObjCClass("NSError")
NSProcessInfo = ObjCClass("NSProcessInfo")

NSKeyValueChangeKey = str
NSKeyValueChangeIndexesKey = objc_const(Foundation, "NSKeyValueChangeIndexesKey")
NSKeyValueChangeKindKey = objc_const(Foundation, "NSKeyValueChangeKindKey")
NSKeyValueChangeNewKey = objc_const(Foundation, "NSKeyValueChangeNewKey")
NSKeyValueChangeNotificationIsPriorKey = objc_const(
    Foundation, "NSKeyValueChangeNotificationIsPriorKey"
)
NSKeyValueChangeOldKey = objc_const(Foundation, "NSKeyValueChangeOldKey")

NSKeyValueObservingOptions = int
NSKeyValueObservingOptionNew = 0x01
NSKeyValueObservingOptionOld = 0x02
NSKeyValueObservingOptionInitial = 0x04
NSKeyValueObservingOptionPrior = 0x08
