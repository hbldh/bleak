import typing

import java.lang

class AdServicesException(java.lang.Exception):
    @typing.overload
    def __init__(self, message: str | java.lang.String, /) -> None: ...
    @typing.overload
    def __init__(self, message: str | java.lang.String, e: java.lang.Throwable, /) -> None: ...
