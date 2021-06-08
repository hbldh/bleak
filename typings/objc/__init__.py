from typing import Type, TypeVar

T = TypeVar("T")


def super(cls: Type[T], self: T) -> T:
    ...
