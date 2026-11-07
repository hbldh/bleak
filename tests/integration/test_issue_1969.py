import asyncio

import pytest
from bumble.att import Attribute
from bumble.device import Device
from bumble.gatt import Characteristic, Service
from bumble.hci import HCI_REMOTE_USER_TERMINATED_CONNECTION_ERROR

from bleak import BleakClient
from bleak.args.bluez import BlueZNotifyArgs
from bleak.backends import BleakBackend, get_default_backend
from bleak.backends.characteristic import BleakGATTCharacteristic
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)

TEST_SERVICE_UUID = "0b1c5a2e-7f0c-4d7e-9a57-2d3c1f0e1969"
TEST_CHARACTERISTIC_UUID = "5c2b8e8a-1f4e-4a55-8c1e-6e0b7a9d1969"


@pytest.mark.parametrize(
    "bluez",
    (
        [{"use_start_notify": True}, {"use_start_notify": False}]
        if get_default_backend() == BleakBackend.BLUEZ_DBUS
        else [{}]
    ),
)
@pytest.mark.parametrize("peripheral_disconnects", [False, True])
async def test_notify_after_reconnect(
    bumble_peripheral: Device, bluez: BlueZNotifyArgs, peripheral_disconnects: bool
) -> None:
    """
    Ensure notifications can be started again and are delivered exactly once
    after disconnecting and reconnecting the same client.

    Regression test for: https://github.com/hbldh/bleak/issues/1969
    """

    test_characteristic = Characteristic[bytes](
        TEST_CHARACTERISTIC_UUID,
        Characteristic.Properties.NOTIFY,
        Attribute.Permissions(0),
    )

    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral, services=[Service(TEST_SERVICE_UUID, [test_characteristic])]
    )

    device = await find_ble_device(bumble_peripheral)

    disconnected = asyncio.Event()

    client = BleakClient(
        device,
        disconnected_callback=lambda _: disconnected.set(),
        services=[TEST_SERVICE_UUID],
    )

    notified_data: asyncio.Queue[bytes] = asyncio.Queue()

    def notify_callback(characteristic: BleakGATTCharacteristic, data: bytearray):
        notified_data.put_nowait(bytes(data))

    try:
        for _ in range(3):
            await client.connect()

            await client.start_notify(
                TEST_CHARACTERISTIC_UUID, notify_callback, bluez=bluez
            )

            await bumble_peripheral.notify_subscribers(  # type: ignore  # (missing type hints in bumble)
                test_characteristic, b"1234"
            )

            data = await asyncio.wait_for(notified_data.get(), timeout=1)
            assert data == b"1234"

            # a notification subscription left over from a previous connection
            # would cause the same notification to be delivered more than once
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(notified_data.get(), timeout=0.5)

            disconnected.clear()

            if peripheral_disconnects:
                connection = next(iter(bumble_peripheral.connections.values()))
                await bumble_peripheral.disconnect(
                    connection, HCI_REMOTE_USER_TERMINATED_CONNECTION_ERROR
                )
                await asyncio.wait_for(disconnected.wait(), timeout=5)

            # disconnect() must still be called to release resources after the
            # peripheral disconnected, before connecting again
            await client.disconnect()
            await asyncio.wait_for(disconnected.wait(), timeout=5)

            await bumble_peripheral.start_advertising()
    finally:
        await client.disconnect()
