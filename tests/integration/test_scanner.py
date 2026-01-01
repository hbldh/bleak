import asyncio
import contextlib
import sys

import pytest
from bumble import data_types
from bumble.core import UUID
from bumble.device import Device

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.uuids import normalize_uuid_str
from tests.integration.conftest import configure_and_power_on_bumble_peripheral

DEFAULT_TIMEOUT = 5.0


async def test_discover(bumble_peripheral: Device):
    """Scanner discovery is finding the device."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

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


async def test_find_by_address(bumble_peripheral: Device):
    """Scanner is finding the device by address."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await BleakScanner.find_device_by_address(
        bumble_peripheral.static_address.to_string(), cb={"use_bdaddr": True}
    )
    assert device is not None


@pytest.mark.parametrize("service_uuid_available", [True, False])
async def test_discover_filter_by_service_uuid(
    bumble_peripheral: Device,
    service_uuid_available: bool,
):
    """Scanner discovery is filtering service uuids correctly."""
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        additional_adv_data=(
            [data_types.IncompleteListOf16BitServiceUUIDs([UUID(0x180F)])]
            if service_uuid_available
            else []
        ),
    )

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
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

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
    assert found_adv_data.platform_data

    # Verify that this value is an integer and not some other
    # type from a ffi binding framework.
    assert isinstance(found_adv_data.rssi, int)

    # The rssi can vary. So we only check for a plausible range.
    assert -127 <= found_adv_data.rssi < 0


async def test_adv_data_complex(bumble_peripheral: Device):
    """Complex advertising data is parsed correct."""
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        [
            data_types.ManufacturerSpecificData(0x1234, b"MFG"),
            data_types.IncompleteListOf16BitServiceUUIDs([UUID(0x180F)]),
            data_types.TxPowerLevel(123),
            data_types.ServiceData16BitUUID(UUID(0x180F), b"SER"),
        ],
    )

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
    assert found_adv_data.platform_data

    # Verify that this value is an integer and not some other
    # type from a ffi binding framework.
    assert isinstance(found_adv_data.rssi, int)

    # The rssi can vary. So we only check for a plausible range.
    assert -127 <= found_adv_data.rssi < 0
