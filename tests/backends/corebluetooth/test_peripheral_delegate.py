import sys

import pytest

if sys.platform != "darwin":
    pytest.skip("CoreBluetooth only tests", allow_module_level=True)
    # unreachable, but makes the type checkers happy
    assert False

from typing import cast
from unittest.mock import Mock

from CoreBluetooth import CBPeripheral

from bleak.backends.corebluetooth.PeripheralDelegate import PeripheralDelegate


async def test_clear_notify_callbacks() -> None:
    """clear_notify_callbacks() removes all notification bookkeeping."""
    delegate = PeripheralDelegate(cast(CBPeripheral, Mock()))

    callbacks = (
        delegate._characteristic_notify_callbacks  # pyright: ignore[reportPrivateUsage]
    )
    discriminators = (
        delegate._characteristic_notification_discriminators  # pyright: ignore[reportPrivateUsage]
    )

    callbacks[42] = lambda data: None
    discriminators[42] = None

    delegate.clear_notify_callbacks()

    assert not callbacks
    assert not discriminators
