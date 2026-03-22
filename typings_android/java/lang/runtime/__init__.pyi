import typing

import java.lang
import java.lang.invoke

class ObjectMethods(java.lang.Object):
    @staticmethod
    def bootstrap(lookup: java.lang.invoke.MethodHandles.Lookup, methodName: str | java.lang.String, type: java.lang.invoke.TypeDescriptor, recordClass: typing.Type[java.lang.Object], names: str | java.lang.String, /, *getters: java.lang.invoke.MethodHandle) -> java.lang.Object: ...
