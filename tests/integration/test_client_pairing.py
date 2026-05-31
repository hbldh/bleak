import pytest
from bumble.device import Device

from bleak import BleakClient
from bleak.backends import BleakBackend, get_default_backend
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)


@pytest.mark.skipif(
    get_default_backend() == BleakBackend.CORE_BLUETOOTH,
    reason="unpair is not available on CoreBluetooth",
)
async def test_unpair_unpaired_device(bumble_peripheral: Device) -> None:
    """unpair() after a connect/disconnect of a never-paired device does not raise."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    client = BleakClient(device)
    await client.connect()
    await client.disconnect()
    await client.unpair()


@pytest.mark.skipif(
    get_default_backend() != BleakBackend.CORE_BLUETOOTH,
    reason="pairing is not possible on CoreBluetooth",
)
async def test_pairing_unavailable(bumble_peripheral: Device) -> None:
    """Check if pairing on CoreBluetooth raises an error."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    client = BleakClient(device)
    with pytest.raises(NotImplementedError):
        await client.pair()
    with pytest.raises(NotImplementedError):
        await client.unpair()
