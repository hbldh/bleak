from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

from typing import Iterator, TypeVar

from java.lang import Iterable
from org.beeware.android import MainActivity

T = TypeVar("T")


def iterate_java_obj(java_iterable: Iterable[T]) -> Iterator[T]:
    iterator = java_iterable.iterator()
    assert iterator is not None
    while iterator.hasNext():
        yield iterator.next()


activity = MainActivity.singletonThis
context = activity.getApplicationContext()
