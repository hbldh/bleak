import sys

import pytest

if sys.platform != "darwin":
    pytest.skip("CoreBluetooth only tests", allow_module_level=True)
    # unreachable, but makes the type checkers happy
    assert False

from typing import cast
from unittest.mock import AsyncMock, Mock, patch

from CoreBluetooth import CBPeripheral

from bleak.backends.corebluetooth.CentralManagerDelegate import (
    CentralManagerDelegate,
    DisconnectCallback,
)
from bleak.backends.corebluetooth.client import BleakClientCoreBluetooth
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError


async def test_disconnect_callback_clears_notify_callbacks() -> None:
    """
    The disconnect callback resets the notification bookkeeping of the
    peripheral delegate, so that ``start_notify()`` works again after
    reconnecting with the same client instance.

    Regression test for: https://github.com/hbldh/bleak/issues/1969
    """
    peripheral = cast(CBPeripheral, Mock())
    disconnect_callbacks: list[DisconnectCallback] = []

    async def connect(
        peripheral: CBPeripheral,
        disconnect_callback: DisconnectCallback,
        timeout: float = 10.0,
    ) -> None:
        disconnect_callbacks.append(disconnect_callback)

    manager = Mock(spec=CentralManagerDelegate)
    manager.connect = connect

    device = BLEDevice(
        "00000000-0000-0000-0000-000000000000", "Test", (peripheral, manager)
    )
    client = BleakClientCoreBluetooth(device, timeout=10.0)

    with patch.object(BleakClientCoreBluetooth, "_get_services", AsyncMock()):
        await client.connect(pair=False)

    delegate = client._delegate  # pyright: ignore[reportPrivateUsage]
    assert delegate is not None

    callbacks = (
        delegate._characteristic_notify_callbacks  # pyright: ignore[reportPrivateUsage]
    )
    discriminators = (
        delegate._characteristic_notification_discriminators  # pyright: ignore[reportPrivateUsage]
    )

    callbacks[42] = lambda data: None
    discriminators[42] = None

    (disconnect_callback,) = disconnect_callbacks
    disconnect_callback()

    assert not callbacks
    assert not discriminators

    # the disconnect callback also fails any pending futures
    with pytest.raises(BleakError, match="disconnected"):
        await delegate._services_discovered_future  # pyright: ignore[reportPrivateUsage]
