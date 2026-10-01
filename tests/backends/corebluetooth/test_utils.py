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

from bleak.backends.corebluetooth.utils import nsdata_to_bdaddr, nsdata_to_bytes


def test_nsdata_to_bytes_does_not_retain_data():
    data = NSData.alloc().initWithBytes_length_(b"test", 4)
    initial_refcount = sys.getrefcount(data)

    for _ in range(10):
        assert nsdata_to_bytes(data) == b"test"

    assert sys.getrefcount(data) == initial_refcount


def test_nsdata_to_bdaddr_does_not_retain_data():
    data = NSData.alloc().initWithBytes_length_(b"\x01\x23\x45\x67\x89\xab", 6)
    initial_refcount = sys.getrefcount(data)

    for _ in range(10):
        assert nsdata_to_bdaddr(data) == "01:23:45:67:89:AB"

    assert sys.getrefcount(data) == initial_refcount
