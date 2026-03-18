import typing

import java
import java.lang
import java.util

class SdkExtensions(java.lang.Object):
    AD_SERVICES: typing.ClassVar[int] = ...
    @staticmethod
    def getAllExtensionVersions() -> java.util.Map[java.lang.Integer, java.lang.Integer]: ...
    @staticmethod
    def getExtensionVersion(extension: int | java.jint | java.lang.Integer, /) -> int: ...
