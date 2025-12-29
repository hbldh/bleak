import asyncio

import pytest
from bumble.device import Connection, Device
from bumble.gatt import Characteristic, CharacteristicValue, Service

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)


async def test_read_gatt_char(bumble_peripheral: Device):
    """Reading a GATT characteristic is possible."""
    READ_SERVICE_UUID = "2908f536-3fab-43c9-a7b2-80b6fdaae99b"
    READ_CHARACTERISITC_UUID = "1a1af049-9c23-4b69-b763-e1096674ed18"
    virtual_characteristic = Characteristic(
        READ_CHARACTERISITC_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"DATA",
    )
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[Service(READ_SERVICE_UUID, [virtual_characteristic])],
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        data = await client.read_gatt_char(READ_CHARACTERISITC_UUID)
        assert data == b"DATA"


async def test_write_gatt_char_with_response(bumble_peripheral: Device):
    """Writing a GATT characteristic is possible."""
    WRITE_WITH_RESPONSE_SERVICE_UUID = "79a92bad-31b4-4a70-885c-e704ae2c6363"
    WRITE_WITH_RESPONSE_CHARACTERISITC_UUID = "2a07f6ea-6401-45d7-838c-0f459a7edb7f"
    virtual_characteristic = Characteristic(
        WRITE_WITH_RESPONSE_CHARACTERISITC_UUID,
        Characteristic.Properties.WRITE,
        Characteristic.WRITEABLE,
        b"----",
    )
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[Service(WRITE_WITH_RESPONSE_SERVICE_UUID, [virtual_characteristic])],
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        await client.write_gatt_char(
            WRITE_WITH_RESPONSE_CHARACTERISITC_UUID, b"DATA", response=True
        )
        assert virtual_characteristic.value == b"DATA"


async def test_write_gatt_char_no_response(bumble_peripheral: Device):
    """Writing a GATT characteristic is possible."""
    WRITE_WITHOUT_RESPONSE_SERVICE_UUID = "79a92bad-31b4-4a70-885c-e704ae2c6363"
    WRITE_WITHOUT_RESPONSE_CHARACTERISITC_UUID = "2a07f6ea-6401-45d7-838c-0f459a7edb7f"

    peripheral_write_callback_called: asyncio.Future[bytes] = asyncio.Future()

    def peripheral_write_callback(connection: Connection, value: bytes):
        if not peripheral_write_callback_called.done():
            peripheral_write_callback_called.set_result(value)

    virtual_characteristic = Characteristic[bytes](
        WRITE_WITHOUT_RESPONSE_CHARACTERISITC_UUID,
        Characteristic.Properties.WRITE_WITHOUT_RESPONSE,
        Characteristic.WRITEABLE,
        CharacteristicValue(write=peripheral_write_callback),
    )
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[
            Service(WRITE_WITHOUT_RESPONSE_SERVICE_UUID, [virtual_characteristic])
        ],
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device) as client:
        await client.write_gatt_char(
            WRITE_WITHOUT_RESPONSE_CHARACTERISITC_UUID, b"DATA", response=False
        )
        written_value = await asyncio.wait_for(
            peripheral_write_callback_called, timeout=1
        )
        assert written_value == b"DATA"


async def test_notify_gatt_char(bumble_peripheral: Device):
    """Writing a GATT characteristic is possible."""
    NOTIFY_SERVICE_UUID = "e405a09d-7c8e-4ac5-adcf-ba808e7f2d18"
    NOTIFY_CHARACTERISITC_UUID = "d4c6dad3-76f1-4034-8871-0a6345be6cfc"
    virtual_characteristic = Characteristic(
        NOTIFY_CHARACTERISITC_UUID,
        Characteristic.Properties.READ | Characteristic.Properties.NOTIFY,
        Characteristic.Permissions.READABLE,
        b"----",
    )
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[Service(NOTIFY_SERVICE_UUID, [virtual_characteristic])],
    )

    device = await find_ble_device(bumble_peripheral)

    notified_data: asyncio.Queue[bytes] = asyncio.Queue()

    def notify_callback(characteristic: BleakGATTCharacteristic, data: bytearray):
        assert characteristic.uuid.lower() == NOTIFY_CHARACTERISITC_UUID
        notified_data.put_nowait(bytes(data))

    async with BleakClient(device) as client:
        await client.start_notify(
            NOTIFY_CHARACTERISITC_UUID,
            notify_callback,
        )
        assert notified_data.empty()

        await bumble_peripheral.notify_subscribers(  # type: ignore
            virtual_characteristic,
            b"1234",
        )

        data = await asyncio.wait_for(notified_data.get(), timeout=1)
        assert data == b"1234"

        await bumble_peripheral.notify_subscribers(  # type: ignore
            virtual_characteristic,
            b"2345",
        )

        data = await asyncio.wait_for(notified_data.get(), timeout=1)
        assert data == b"2345"

        await client.stop_notify(NOTIFY_CHARACTERISITC_UUID)

        await bumble_peripheral.notify_subscribers(  # type: ignore
            virtual_characteristic,
            b"2345",
        )

        # Verify no notification was received
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(notified_data.get(), timeout=1)
