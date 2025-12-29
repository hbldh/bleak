import sys
from typing import TYPE_CHECKING

import pytest
from bumble.device import Device

from bleak import BleakClient
from bleak.backends import BleakBackend, get_default_backend
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)


@pytest.mark.skipif(
    get_default_backend() != BleakBackend.CORE_BLUETOOTH,
    reason="'get_rssi()' is only available on CoreBluetooth",
)
async def test_get_rssi(bumble_peripheral: Device):
    """Getting RSSI from client is possible."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        if TYPE_CHECKING:
            if sys.platform != "darwin":
                assert False, "This backend is only available on macOS"
        from bleak.backends.corebluetooth.client import BleakClientCoreBluetooth

        backend = client._backend  # pyright: ignore[reportPrivateUsage]
        assert isinstance(backend, BleakClientCoreBluetooth)
        rssi = await backend.get_rssi()

        # Verify that this value is an integer and not some other
        # type from a ffi binding framework.
        assert isinstance(rssi, int)

        # The rssi can vary. So we only check for a plausible range.
        assert -127 <= rssi < 0


async def test_mtu_size(bumble_peripheral: Device):
    """Check if the mtu size can be optained."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        if client.backend_id == BleakBackend.BLUEZ_DBUS:
            with pytest.warns(UserWarning):
                mtu_size = client.mtu_size
        else:
            mtu_size = client.mtu_size

        # Verify that this value is an integer and not some other
        # type from a ffi binding framework.
        assert isinstance(mtu_size, int)

        # The mtu_size is different between different platforms. So we only check
        # for a plausible range.
        assert 23 <= mtu_size <= 517
