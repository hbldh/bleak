import asyncio
import sys

import pytest
from bumble import data_types
from bumble.core import UUID, AdvertisingData
from bumble.transport.common import Transport

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from tests.integration.conftest import create_bumble_peripheral

DEFAULT_TIMEOUT = 5.0


async def test_discover(hci_transport: Transport):
    """Scanner discovery is finding the device."""
    peripheral = create_bumble_peripheral(hci_transport)
    peripheral.advertising_data = bytes(
        AdvertisingData(
            [
                data_types.Flags(
                    AdvertisingData.Flags.LE_GENERAL_DISCOVERABLE_MODE
                    | AdvertisingData.Flags.BR_EDR_NOT_SUPPORTED
                ),
                data_types.CompleteLocalName(peripheral.name),
            ]
        ),
    )
    await peripheral.power_on()
    await peripheral.start_advertising()

    devices = await BleakScanner.discover(return_adv=True, timeout=DEFAULT_TIMEOUT)
    filtered_devices = list(
        filter(lambda device: device[1].local_name == peripheral.name, devices.values())
    )

    assert len(filtered_devices) == 1
    assert filtered_devices[0][1].local_name == peripheral.name
    if sys.platform != "darwin":
        # accessing the address is not possible on macOS
        assert filtered_devices[0][0].address == str(peripheral.static_address)


@pytest.mark.parametrize("service_uuid_available", [True, False])
async def test_discover_filter_by_service_uuid(
    hci_transport: Transport, service_uuid_available: bool
):
    """Scanner discovery is filtering service uuids correctly."""
    peripheral = create_bumble_peripheral(hci_transport)
    if service_uuid_available:
        peripheral.advertising_data = bytes(
            AdvertisingData(
                [
                    data_types.Flags(
                        AdvertisingData.Flags.LE_GENERAL_DISCOVERABLE_MODE
                        | AdvertisingData.Flags.BR_EDR_NOT_SUPPORTED
                    ),
                    data_types.CompleteLocalName(peripheral.name),
                    data_types.IncompleteListOf16BitServiceUUIDs([UUID(0x180F)]),
                ]
            ),
        )
    else:
        peripheral.advertising_data = bytes(
            AdvertisingData(
                [
                    data_types.Flags(
                        AdvertisingData.Flags.LE_GENERAL_DISCOVERABLE_MODE
                        | AdvertisingData.Flags.BR_EDR_NOT_SUPPORTED
                    ),
                    data_types.CompleteLocalName(peripheral.name),
                ]
            ),
        )
    await peripheral.power_on()
    await peripheral.start_advertising()

    found_adv_data: AdvertisementData | None = None
    device_found_event = asyncio.Event()

    def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
        nonlocal found_adv_data
        if device.name == peripheral.name:
            found_adv_data = adv_data
            device_found_event.set()

    async with BleakScanner(
        detection_callback,
        service_uuids=["0000180f-0000-1000-8000-00805f9b34fb"],
    ):
        if service_uuid_available:
            await asyncio.wait_for(device_found_event.wait(), timeout=DEFAULT_TIMEOUT)
        else:
            await asyncio.sleep(DEFAULT_TIMEOUT)

    if service_uuid_available:
        assert found_adv_data is not None
    else:
        assert found_adv_data is None


async def test_adv_data_simple(hci_transport: Transport):
    """Simple advertising data is parsed correct."""
    peripheral = create_bumble_peripheral(hci_transport)
    peripheral.advertising_data = bytes(
        AdvertisingData(
            [
                data_types.Flags(
                    AdvertisingData.Flags.LE_GENERAL_DISCOVERABLE_MODE
                    | AdvertisingData.Flags.BR_EDR_NOT_SUPPORTED
                ),
                data_types.CompleteLocalName(peripheral.name),
            ]
        ),
    )
    await peripheral.power_on()
    await peripheral.start_advertising()

    found_adv_data: AdvertisementData | None = None
    device_found_event = asyncio.Event()

    def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
        nonlocal found_adv_data
        if device.name == peripheral.name:
            found_adv_data = adv_data
            device_found_event.set()

    async with BleakScanner(detection_callback):
        await asyncio.wait_for(device_found_event.wait(), timeout=DEFAULT_TIMEOUT)

    assert found_adv_data is not None
    assert found_adv_data.local_name == peripheral.name
    assert found_adv_data.manufacturer_data == {}
    assert found_adv_data.service_data == {}
    assert found_adv_data.service_uuids == []
    assert found_adv_data.tx_power is None
    assert isinstance(found_adv_data.rssi, int)
    assert found_adv_data.platform_data


async def test_adv_data_complex(hci_transport: Transport):
    """Complex advertising data is parsed correct."""
    peripheral = create_bumble_peripheral(hci_transport)
    peripheral.advertising_data = bytes(
        AdvertisingData(
            [
                data_types.Flags(
                    AdvertisingData.Flags.LE_GENERAL_DISCOVERABLE_MODE
                    | AdvertisingData.Flags.BR_EDR_NOT_SUPPORTED
                ),
                data_types.CompleteLocalName(peripheral.name),
                data_types.ManufacturerSpecificData(0x1234, b"MFG"),
                data_types.IncompleteListOf16BitServiceUUIDs([UUID(0x180F)]),
                data_types.TxPowerLevel(123),
                data_types.ServiceData16BitUUID(UUID(0x180F), b"SER"),
            ]
        )
    )
    await peripheral.power_on()
    await peripheral.start_advertising()

    found_adv_data: AdvertisementData | None = None
    device_found_event = asyncio.Event()

    def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
        nonlocal found_adv_data
        if device.name == peripheral.name:
            found_adv_data = adv_data
            device_found_event.set()

    async with BleakScanner(detection_callback):
        await asyncio.wait_for(device_found_event.wait(), timeout=DEFAULT_TIMEOUT)

    assert found_adv_data is not None
    assert found_adv_data.local_name == peripheral.name
    assert found_adv_data.manufacturer_data == {0x1234: b"MFG"}
    assert found_adv_data.service_data == {
        "0000180f-0000-1000-8000-00805f9b34fb": b"SER"
    }
    assert found_adv_data.service_uuids == ["0000180f-0000-1000-8000-00805f9b34fb"]
    assert found_adv_data.tx_power == 123
    assert isinstance(found_adv_data.rssi, int)
    assert found_adv_data.platform_data
