import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import pytest

# isort: off

if not sys.platform.startswith("darwin"):
    pytest.skip("backend only available on macOS", allow_module_level=True)

import objc
from Foundation import NSData

from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth


async def test_use_bdaddr_does_not_retain_address_data(monkeypatch: pytest.MonkeyPatch):
    address_data = NSData.alloc().initWithBytes_length_(b"\x01\x23\x45\x67\x89\xab", 6)
    manager = Mock(
        callbacks={},
        wait_until_ready=AsyncMock(),
        start_scan=AsyncMock(),
        stop_scan=AsyncMock(),
    )
    manager.central_manager.retrieveAddressForPeripheral_.return_value = address_data
    monkeypatch.setattr(
        "bleak.backends.corebluetooth.scanner.CentralManagerDelegate", lambda: manager
    )
    peripheral = Mock()
    peripheral.identifier().UUIDString.return_value = (
        "00000000-0000-0000-0000-000000000001"
    )
    peripheral.name.return_value = "Test device"
    scanner = BleakScannerCoreBluetooth(None, None, "active", cb={"use_bdaddr": True})
    await scanner.start()
    initial_refcount = sys.getrefcount(address_data)

    for _ in range(10):
        with objc.autorelease_pool():
            manager.callbacks[id(scanner)](peripheral, {}, -60)

    await scanner.stop()
    device, _ = next(iter(scanner.seen_devices.values()))
    assert device.address == "01:23:45:67:89:AB"
    assert sys.getrefcount(address_data) == initial_refcount
