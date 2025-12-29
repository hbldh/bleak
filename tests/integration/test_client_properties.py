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
        rssi = await client._backend.get_rssi()  # type: ignore
        assert isinstance(rssi, int)


async def test_mtu_size(bumble_peripheral: Device):
    """Check if the mtu size can be optained."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        # The mtu_size is different between different platforms. So it is not possible
        # to get a reliable value. So we only check that it is an int.
        assert isinstance(client.mtu_size, int)
