import pytest
from bumble.att import Attribute
from bumble.device import Device
from bumble.gatt import Characteristic, Service

from bleak import BleakClient
from bleak.backends import BleakBackend, get_default_backend
from bleak.backends.characteristic import BleakGATTCharacteristic
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)

TEST_SERVICE_UUID = "08a67ad7-22ca-4e06-89a0-c6cfe0c76471"
TEST_CHARACTERISTIC_UUID = "797f54d7-83d1-49c7-9992-0d0b136117dd"


@pytest.mark.skipif(
    get_default_backend() != BleakBackend.CORE_BLUETOOTH,
    reason="issue present in Core Bluetooth backend only",
)
async def test_start_notify_after_reconnect(bumble_peripheral: Device) -> None:
    """
    Ensure notifications can be started again after disconnecting and reconnecting.

    The Core Bluetooth backend reuses its peripheral delegate when the same
    client instance reconnects, so the notification bookkeeping has to be
    cleared on disconnect, otherwise start_notify() raises
    ``ValueError("Characteristic notifications already started")``.

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

    def notify_callback(
        characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        pass

    client = BleakClient(device, services=[TEST_SERVICE_UUID])

    async with client:
        await client.start_notify(TEST_CHARACTERISTIC_UUID, notify_callback)

    await bumble_peripheral.start_advertising()

    # Reusing the same client instance keeps the backend state from the first
    # connection, which is what triggered the issue.
    async with client:
        await client.start_notify(TEST_CHARACTERISTIC_UUID, notify_callback)
