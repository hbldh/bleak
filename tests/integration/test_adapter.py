import asyncio
import dataclasses
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from bumble import data_types
from bumble.core import UUID
from bumble.device import Device
from bumble.gatt import Characteristic, Service
from bumble.transport.common import Transport

from bleak import BleakAdapter, BleakClient
from bleak.backends import BleakBackend, get_default_backend
from bleak.backends.device import BLEDevice
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    create_bumble_peripheral,
    create_hci_transport,
    find_ble_device,
)

# Custom UUIDs ensure we don't accidentally match real connected devices.
TEST_SERVICE_UUID = "a87a0e5e-7b5d-4f2e-9c3a-1d8f6b2e4c7a"
TEST_CHAR_UUID = "b1e2f3a4-5c6d-7e8f-9a0b-1c2d3e4f5a6b"
OTHER_SERVICE_UUID = "c3d4e5f6-7a8b-9c0d-1e2f-3a4b5c6d7e8f"


@dataclasses.dataclass
class ConnectedPeripheral:
    client: BleakClient
    device: BLEDevice


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def hci_transport(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[Transport, None]:
    """Create a bumble HCI Transport."""
    async with create_hci_transport(request) as hci_transport:
        yield hci_transport


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def bumble_peripheral(hci_transport: Transport) -> Device:
    """Create a BLE peripheral device with bumble."""
    return create_bumble_peripheral(hci_transport)


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def connected_peripheral(
    bumble_peripheral: Device,
) -> AsyncGenerator[ConnectedPeripheral, None]:
    test_characteristic = Characteristic[bytes](
        TEST_CHAR_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"\x64",
    )

    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        additional_adv_data=[
            data_types.IncompleteListOf128BitServiceUUIDs([UUID(TEST_SERVICE_UUID)])
        ],
        services=[Service(TEST_SERVICE_UUID, [test_characteristic])],
    )

    device = await find_ble_device(bumble_peripheral)

    # Ensure the device is connected before yielding, since the tests require it
    # to be connected to be valid.
    async with BleakClient(device) as client:
        yield ConnectedPeripheral(client=client, device=device)


@pytest.mark.asyncio(loop_scope="module")
async def test_get_connected_devices_without_filters_returns_non_empty(
    connected_peripheral: ConnectedPeripheral,
) -> None:
    """Calling get_connected_devices() without filters returns connected devices."""
    adapter = await BleakAdapter.get()

    connected_devices = await adapter.get_connected_devices()

    assert connected_devices


@pytest.mark.asyncio(loop_scope="module")
async def test_get_connected_devices_filters_by_service_uuid(
    connected_peripheral: ConnectedPeripheral,
) -> None:
    """Connected devices are filtered to the requested service UUID."""
    adapter = await BleakAdapter.get()

    connected_devices = await adapter.get_connected_devices([TEST_SERVICE_UUID])

    assert [d.address for d in connected_devices] == [
        connected_peripheral.device.address
    ]

    not_connected = await adapter.get_connected_devices([OTHER_SERVICE_UUID])
    assert not_connected == []


@pytest.mark.asyncio(loop_scope="module")
async def test_disconnect_does_not_disconnect_connected_device(
    connected_peripheral: ConnectedPeripheral,
) -> None:
    """A BleakClient using a device from get_connected_devices() must not
    disconnect the underlying connection on close.
    """
    adapter = await BleakAdapter.get()
    connected_devices = await adapter.get_connected_devices([TEST_SERVICE_UUID])
    target = next(
        d for d in connected_devices if d.address == connected_peripheral.device.address
    )

    async with BleakClient(target) as client:
        # If this is false, it is a bug in Bleak. Real usage never needs
        # to check `is_connected` after connecting because it cannot be
        # anything but true. If connecting fails, an exception is raised
        # before we get here.
        assert client.is_connected

    assert connected_peripheral.client.is_connected


@pytest.mark.asyncio(loop_scope="module")
async def test_disconnect_of_originating_client_disconnects_attached_client(
    connected_peripheral: ConnectedPeripheral,
) -> None:
    """When the BleakClient that originally established the connection
    disconnects, the attached BleakClient (using a device from
    get_connected_devices()) sees the disconnect on BlueZ but stays
    connected on other backends.
    """
    adapter = await BleakAdapter.get()
    connected_devices = await adapter.get_connected_devices([TEST_SERVICE_UUID])
    target = next(
        d for d in connected_devices if d.address == connected_peripheral.device.address
    )

    # NOTE: this test must be the last in the module since it leaves the
    # fixture's BleakClient in a disconnected state. Reconnecting Bumble
    # immediately after a cascading disconnect is unreliable.
    async with BleakClient(target) as client:
        await connected_peripheral.client.disconnect()
        await asyncio.sleep(0.5)
        if get_default_backend() == BleakBackend.BLUEZ_DBUS:
            # BlueZ does not ref-count connections, so any client tearing
            # down the connection takes everyone else with it. See
            # https://github.com/bluez/bluez/issues/89.
            assert not client.is_connected
        else:
            # Other backends ref-count and keep the attached client
            # connected when the originating one disconnects.
            assert client.is_connected
