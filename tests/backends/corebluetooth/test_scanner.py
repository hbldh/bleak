import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import pytest

# isort: off

if not sys.platform.startswith("darwin"):
    pytest.skip("backend only available on macOS", allow_module_level=True)

from Foundation import NSData

from bleak.backends.corebluetooth.scanner import (
    _nsdata_to_bytes,  # pyright: ignore[reportPrivateUsage]
)


def test_nsdata_to_bytes_does_not_retain_data():
    data = NSData.alloc().initWithBytes_length_(b"test", 4)
    initial_refcount = sys.getrefcount(data)

    for _ in range(10):
        assert _nsdata_to_bytes(data) == b"test"

    assert sys.getrefcount(data) == initial_refcount
