import asyncio

from bumble.att import Attribute, AttributeValue
from bumble.device import Connection, Device
from bumble.gatt import (
    GATT_CLIENT_CHARACTERISTIC_CONFIGURATION_DESCRIPTOR,
    Characteristic,
    Descriptor,
    Service,
)

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)

TEST_SERVICE_UUID = "9d513f40-5c89-42dc-9688-2cfa30f2d9e7"
TEST_CHARACTERISTIC_UUID = "e809cb2f-34e3-42a1-ba92-22db2495cd6a"


async def test_notification_sent_before_write_response(
    bumble_peripheral: Device,
) -> None:
    """
    Regression test for <https://github.com/hbldh/bleak/issues/1885>.
    """

    notifications_enabled = False

    def on_cccd_read(connection: Connection) -> bytes:
        return b"\x01\x00" if notifications_enabled else b"\x00\x00"

    async def on_cccd_write(connection: Connection, value: bytes) -> None:
        nonlocal notifications_enabled
        notifications_enabled = value == b"\x01\x00"

        # This is simulating an unusual peripheral that sends a notification
        # immediately upon receiving the CCCD write, before sending the write
        # response.

        # TODO: Type hints in bumble need to be fixed to be able to remove the pyright ignore
        await bumble_peripheral.notify_subscribers(  # pyright: ignore[reportUnknownMemberType]
            test_characteristic, b"test", force=True
        )

    cccd_value = AttributeValue[bytes](on_cccd_read, on_cccd_write)

    test_characteristic = Characteristic[bytes](
        TEST_CHARACTERISTIC_UUID,
        Characteristic.Properties.NOTIFY,
        Attribute.Permissions(0),
        descriptors=[
            Descriptor(
                GATT_CLIENT_CHARACTERISTIC_CONFIGURATION_DESCRIPTOR,
                Attribute.Permissions.WRITEABLE | Attribute.Permissions.READABLE,
                cccd_value,
            )
        ],
    )

    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral, services=[Service(TEST_SERVICE_UUID, [test_characteristic])]
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device, services=[TEST_SERVICE_UUID]) as client:
        notification_queue: asyncio.Queue[bytes] = asyncio.Queue()

        def on_notification(_: BleakGATTCharacteristic, data: bytearray) -> None:
            notification_queue.put_nowait(bytes(data))

        await client.start_notify(
            TEST_CHARACTERISTIC_UUID, on_notification, bluez={"use_start_notify": True}
        )

        # In BlueZ, the notification is not received when using "AcquireNotify"
        # causing this to timeout.

        data = await asyncio.wait_for(notification_queue.get(), timeout=3)

        assert data == b"test"
