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
    reason="pairing is not possible on CoreBluetooth",
)
async def test_pairing_unavailable(bumble_peripheral: Device):
    """Check if pairing on CoreBluetooth raises an error."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    client = BleakClient(device)
    with pytest.raises(NotImplementedError):
        await client.pair()
    with pytest.raises(NotImplementedError):
        await client.unpair()


@pytest.mark.skipif(
    get_default_backend() != BleakBackend.ANDROID,
    reason="testing pairing is currently only implemented for the Android backend",
)
async def test_pairing_android(bumble_peripheral: Device):
    """Test pairing on Android backend."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        # Pairing (Bonding) should succeed without raising an exception
        await client.pair()

        # Unpairing (Unbonding) is not possible on Android backend, because
        # Android does not provide an API to unpair programmatically. So
        # we check that NotImplementedError is raised.
        with pytest.raises(NotImplementedError):
            await client.unpair()


# TODO: Add tests for pairing
