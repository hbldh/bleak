import asyncio

import pytest
from bumble.device import Device

from bleak import BleakClient
from bleak._compat import timeout as async_timeout
from bleak.backends import BleakBackend, get_default_backend
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)


async def test_connect(bumble_peripheral: Device):
    """Connecting to a BLE device is possible."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        assert client.name == bumble_peripheral.name


async def test_connect_multiple_times(bumble_peripheral: Device):
    """Connecting to a BLE device multiple times is possible."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device):
        pass

    await bumble_peripheral.start_advertising()

    async with BleakClient(device):
        pass


async def test_connect_timeout(bumble_peripheral: Device):
    """Connecting to a removed BLE device times out."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    await bumble_peripheral.stop_advertising()

    with pytest.raises(asyncio.TimeoutError):
        async with BleakClient(device, timeout=1.0):
            pass


async def test_is_connected(bumble_peripheral: Device):
    """Check if a connection is connected is working."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    client = BleakClient(device)

    assert client.is_connected is False
    async with BleakClient(device) as client:
        assert client.is_connected is True
    assert client.is_connected is False


@pytest.mark.skipif(
    get_default_backend() != BleakBackend.BLUEZ_DBUS,
    reason="reuse-existing-connection behavior is BlueZ-specific",
)
async def test_disconnect_does_not_disconnect_already_connected_device(
    bumble_peripheral: Device,
):
    """A second BleakClient that finds the device already connected must not
    disconnect it when closed. See https://github.com/bluez/bluez/issues/89.
    """
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as outer_client:
        # Nested BleakClients are not a supported usage pattern, but it
        # is the simplest way to exercise the already-connected code path.
        async with BleakClient(device) as inner_client:
            # If this is false, it is a bug in Bleak. Real usage never needs
            # to check `is_connected` after connecting because it cannot be
            # anything but true. If connecting fails, an exception is raised
            # before we get here.
            assert inner_client.is_connected

        assert (
            outer_client.is_connected
        ), "inner client disconnect should not disconnect outer client"


async def test_disconnect_callback(bumble_peripheral: Device):
    """Check if disconnect callback is called."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    disconnected_client_future: asyncio.Future[BleakClient] = asyncio.Future()

    def disconnected_callback(client: BleakClient):
        disconnected_client_future.set_result(client)

    async with BleakClient(device, disconnected_callback) as client:
        # Disconnect from virtual device side
        virtual_connection = list(bumble_peripheral.connections.values())[0]
        await virtual_connection.disconnect()

        # Wait for disconnected callback to be called
        async with async_timeout(5):
            disconnected_client = await disconnected_client_future
        assert disconnected_client is client
