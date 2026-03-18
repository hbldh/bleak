import typing

from java.lang import Object, Throwable
from java.primitive import (
    Primitive,
    jboolean,
    jbyte,
    jchar,
    jdouble,
    jfloat,
    jint,
    jlong,
    jshort,
)

# class.pxi #######################################################################################
def jclass(clsname: str) -> type[Object]: ...

# array.pxi #######################################################################################
_JAVA_OBJ = Primitive | Object

JAVA_OBJ_T = typing.TypeVar("JAVA_OBJ_T", bound=_JAVA_OBJ)

class JavaArray(Object, typing.Sequence[JAVA_OBJ_T]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[JAVA_OBJ_T],
    ): ...
    def __len__(self): ...
    @typing.overload
    def __getitem__(
        self,
        key: int,
    ) -> JAVA_OBJ_T: ...
    @typing.overload
    def __getitem__(
        self,
        key: slice,
    ) -> JavaArray[JAVA_OBJ_T]: ...
    def copy(self) -> JavaArray[JAVA_OBJ_T]: ...
    def __copy__(self) -> JavaArray[JAVA_OBJ_T]: ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: JAVA_OBJ_T,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[JAVA_OBJ_T],
    ): ...
    def __eq__(self, other: typing.Any) -> bool: ...
    def __add__(self, other: JavaArray[JAVA_OBJ_T]) -> JavaArray[JAVA_OBJ_T]: ...
    def __radd__(self, other: JavaArray[JAVA_OBJ_T]) -> JavaArray[JAVA_OBJ_T]: ...
    def __contains__(self, value: typing.Any): ...
    def __iter__(self) -> typing.Iterator[JAVA_OBJ_T]: ...
    def __reversed__(self) -> typing.Iterator[JAVA_OBJ_T]: ...
    def index(self, value: typing.Any, start: int = 0, stop: int = ...) -> int: ...
    def count(self, value: typing.Any) -> int: ...

# inference of correct type is not working, when overloading __init__ with mypy v1.15.0
class JavaArrayJBoolean(JavaArray[jboolean]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jboolean | bool],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: jboolean | bool,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jboolean | bool],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJByte(JavaArray[jbyte]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jbyte | int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: jbyte | int,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jbyte | int],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJShort(JavaArray[jshort]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jshort | int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: jshort | int,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jshort | int],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJInt(JavaArray[jint]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jint | int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: jint | int,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jint | int],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJLong(JavaArray[jlong]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jlong | int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: jlong | int,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jlong | int],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJFloat(JavaArray[jfloat]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jfloat | float],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: jfloat | float,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jfloat | float],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJDouble(JavaArray[jdouble]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jdouble | float],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: jdouble | float,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jdouble | float],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJChar(JavaArray[jchar]):
    def __init__(
        self,
        length_or_value: int | typing.Sequence[jchar | str] | str,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: str,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[jchar | str] | str,
    ): ...
    

@typing.overload
def jarray(
    element_type: typing.Type[jboolean],
) -> typing.Type[JavaArrayJBoolean]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jbyte],
) -> typing.Type[JavaArrayJByte]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jshort],
) -> typing.Type[JavaArrayJShort]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jint],
) -> typing.Type[JavaArrayJInt]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jlong],
) -> typing.Type[JavaArrayJLong]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jfloat],
) -> typing.Type[JavaArrayJFloat]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jdouble],
) -> typing.Type[JavaArrayJDouble]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jchar],
) -> typing.Type[JavaArrayJChar]: ...
@typing.overload
def jarray(
    element_type: typing.Type[JAVA_OBJ_T],
) -> typing.Type[JavaArray[JAVA_OBJ_T]]: ...
@typing.overload
def jarray(element_type: str) -> typing.Type[JavaArray[typing.Any]]: ...

# import.pxi #######################################################################################
def set_import_enabled(enable: bool): ...

# proxy.pxi #######################################################################################
T = typing.TypeVar("T")

@typing.overload
def dynamic_proxy(
    __i1: typing.Type[T],
) -> typing.Type[T]: ...
@typing.overload
def dynamic_proxy(
    # intersection of classes is not supported in type hints, so we use Any here
    *implements: typing.Type[typing.Any],
) -> typing.Type[typing.Any]: ...

JAVA_CLASS_T = typing.TypeVar("JAVA_CLASS_T", bound=Object)

@typing.overload
def static_proxy(
    extends: typing.Type[JAVA_CLASS_T],
    # intersection of classes is not supported in type hints, so we use Any here
    *implements: typing.Type[typing.Any],
    package: str | None = ...,
    modifiers: str = "public",
) -> typing.Type[JAVA_CLASS_T]: ...
@typing.overload
def static_proxy(
    extends: None = ...,
    # intersection of classes is not supported in type hints, so we use Any here
    *implements: typing.Type[typing.Any],
    package: str | None = ...,
    modifiers: str = "public",
) -> typing.Type[Object]: ...
def constructor(
    arg_types: typing.Sequence[typing.Type[_JAVA_OBJ]],
    *,
    modifiers: str = "public",
    throws: typing.Sequence[typing.Type[Throwable]] | None = None,
) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Callable[..., typing.Any]]: ...
def method(
    return_type: typing.Type[_JAVA_OBJ],
    arg_types: typing.Sequence[typing.Type[_JAVA_OBJ]],
    *,
    modifiers: str = "public",
    throws: typing.Sequence[typing.Type[Throwable]] | None = None,
) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Callable[..., typing.Any]]: ...
def Override(
    return_type: typing.Type[_JAVA_OBJ],
    arg_types: typing.Sequence[typing.Type[_JAVA_OBJ]],
    *,
    modifiers: str = "public",
    throws: typing.Sequence[typing.Type[Throwable]] | None = None,
) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Callable[..., typing.Any]]: ...

# utils.pxi #######################################################################################
def cast(cls: typing.Type[T], obj: typing.Any) -> T: ...

# jvm.pxi #######################################################################################
def detach() -> None: ...
