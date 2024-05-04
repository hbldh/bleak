from typing import Optional, Type, TypeVar

from Foundation import NSObject

T = TypeVar("T")


def super(cls: Type[T], self: T) -> T: ...


def macos_available(major: int, minor: int, patch: int = 0) -> bool: ...


class WeakRef:
    def __init__(self, object: NSObject) -> None: ...

    def __call__(self) -> Optional[NSObject]: ...
