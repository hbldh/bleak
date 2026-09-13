import asyncio

import pytest
from bumble.att import Attribute
from bumble.device import Device
from bumble.gatt import Characteristic, Service
from bumble.hci import HCI_REMOTE_USER_TERMINATED_CONNECTION_ERROR

from bleak import BleakClient
from bleak.backends import BleakBackend, get_default_backend
from bleak.backends.characteristic import BleakGATTCharacteristic
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)

TEST_SERVICE_UUID = "9d513f40-5c89-42dc-9688-2cfa30f2d9e7"
TEST_CHARACTERISTIC_UUID = "e809cb2f-34e3-42a1-ba92-22db2495cd6a"


@pytest.mark.skipif(
    get_default_backend() != BleakBackend.BLUEZ_DBUS,
    reason="issue present in BlueZ backend only",
)
async def test_empty_notification_disconnect_disambiguation(
    bumble_peripheral: Device,
) -> None:
    """
    Ensure disconnecting an active notification stream does not deliver EOF as b"".

    This is a weird case that only affects BlueZ when use_start_notify is False.

    Regression test for: https://github.com/hbldh/bleak/issues/1982
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

    async with BleakClient(device, services=[TEST_SERVICE_UUID]) as client:

        notified_data: asyncio.Queue[bytes] = asyncio.Queue()

        def notify_callback(characteristic: BleakGATTCharacteristic, data: bytearray):
            assert characteristic.uuid.lower() == TEST_CHARACTERISTIC_UUID
            notified_data.put_nowait(bytes(data))

        await client.start_notify(
            TEST_CHARACTERISTIC_UUID,
            notify_callback,
            bluez={"use_start_notify": False},
        )

        connection = next(iter(bumble_peripheral.connections.values()))

        await bumble_peripheral.disconnect(
            connection, HCI_REMOTE_USER_TERMINATED_CONNECTION_ERROR
        )

        # A closed AcquireNotify fd/disconnect must not be surfaced as an empty notification.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(notified_data.get(), timeout=1)
