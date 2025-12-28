import asyncio
import contextlib
import sys

import pytest
from bumble import data_types
from bumble.core import UUID, DataType
from bumble.device import Device

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.uuids import normalize_uuid_str
from tests.integration.conftest import add_default_advertising_data

DEFAULT_TIMEOUT = 5.0


async def test_discover(bumble_peripheral: Device):
    """Scanner discovery is finding the device."""
    add_default_advertising_data(bumble_peripheral)
    await bumble_peripheral.power_on()
    await bumble_peripheral.start_advertising()

    devices = await BleakScanner.discover(return_adv=True)
    filtered_devices = list(
        filter(
            lambda device: device[1].local_name == bumble_peripheral.name,
            devices.values(),
        )
    )

    assert len(filtered_devices) == 1
    assert filtered_devices[0][1].local_name == bumble_peripheral.name
    if sys.platform != "darwin":
        # accessing the address is not possible on macOS
        assert filtered_devices[0][0].address == str(bumble_peripheral.static_address)


@pytest.mark.parametrize("service_uuid_available", [True, False])
async def test_discover_filter_by_service_uuid(
    bumble_peripheral: Device,
    service_uuid_available: bool,
):
    """Scanner discovery is filtering service uuids correctly."""
    additional_adv_data: list[DataType] = []
    if service_uuid_available:
        additional_adv_data = [
            data_types.IncompleteListOf16BitServiceUUIDs([UUID(0x180F)])
        ]

    add_default_advertising_data(bumble_peripheral, additional_adv_data)
    await bumble_peripheral.power_on()
    await bumble_peripheral.start_advertising()

    found_adv_data_future: asyncio.Future[AdvertisementData] = asyncio.Future()

    def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
        if device.name == bumble_peripheral.name:
            found_adv_data_future.set_result(adv_data)

    async with BleakScanner(
        detection_callback,
        service_uuids=[normalize_uuid_str("180f")],
    ):
        found_adv_data = None
        with contextlib.suppress(asyncio.TimeoutError):
            found_adv_data = await asyncio.wait_for(
                found_adv_data_future, timeout=DEFAULT_TIMEOUT
            )

    if service_uuid_available:
        assert found_adv_data is not None
    else:
        assert found_adv_data is None


async def test_adv_data_simple(bumble_peripheral: Device):
    """Simple advertising data is parsed correct."""
    add_default_advertising_data(bumble_peripheral)
    await bumble_peripheral.power_on()
    await bumble_peripheral.start_advertising()

    found_adv_data_future: asyncio.Future[AdvertisementData] = asyncio.Future()

    def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
        if device.name == bumble_peripheral.name:
            found_adv_data_future.set_result(adv_data)

    async with BleakScanner(detection_callback):
        found_adv_data = await asyncio.wait_for(
            found_adv_data_future, timeout=DEFAULT_TIMEOUT
        )

    assert found_adv_data is not None
    assert found_adv_data.local_name == bumble_peripheral.name
    assert found_adv_data.manufacturer_data == {}
    assert found_adv_data.service_data == {}
    assert found_adv_data.service_uuids == []
    assert found_adv_data.tx_power is None
    assert isinstance(found_adv_data.rssi, int)
    assert found_adv_data.platform_data


async def test_adv_data_complex(bumble_peripheral: Device):
    """Complex advertising data is parsed correct."""
    add_default_advertising_data(
        bumble_peripheral,
        [
            data_types.ManufacturerSpecificData(0x1234, b"MFG"),
            data_types.IncompleteListOf16BitServiceUUIDs([UUID(0x180F)]),
            data_types.TxPowerLevel(123),
            data_types.ServiceData16BitUUID(UUID(0x180F), b"SER"),
        ],
    )
    await bumble_peripheral.power_on()
    await bumble_peripheral.start_advertising()

    found_adv_data_future: asyncio.Future[AdvertisementData] = asyncio.Future()

    def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
        if device.name == bumble_peripheral.name:
            found_adv_data_future.set_result(adv_data)

    async with BleakScanner(detection_callback):
        found_adv_data = await asyncio.wait_for(
            found_adv_data_future, timeout=DEFAULT_TIMEOUT
        )

    assert found_adv_data is not None
    assert found_adv_data.local_name == bumble_peripheral.name
    assert found_adv_data.manufacturer_data == {0x1234: b"MFG"}
    assert found_adv_data.service_data == {
        "0000180f-0000-1000-8000-00805f9b34fb": b"SER"
    }
    assert found_adv_data.service_uuids == ["0000180f-0000-1000-8000-00805f9b34fb"]
    assert found_adv_data.tx_power == 123
    assert isinstance(found_adv_data.rssi, int)
    assert found_adv_data.platform_data
