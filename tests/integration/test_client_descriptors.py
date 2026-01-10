import dataclasses
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from bumble import gatt
from bumble.core import UUID
from bumble.device import Device
from bumble.gatt import Characteristic, Descriptor, Service
from bumble.transport.common import Transport

from bleak import BleakClient
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    create_bumble_peripheral,
    create_hci_transport,
    find_ble_device,
)


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


DESCR_TEST_SERVICE_UUID = "0d15eded-4e68-4718-bedf-736847b68e72"

READABLE_DESCR_CHAR_UUID = "25c614ab-1560-46da-94bc-c146addfc359"
WRITABLE_DESCR_CHAR_UUID = "822afd2f-c2b2-4302-9edb-09850a93b707"

CUSTOM_BINARY_DESCRIPTOR_UUID = UUID("a1b2c3d4-e5f6-7890-1234-56789abcdef0")
# CoreBluetooth specific UUID
L2CAPPPSM_DESCRIPTOR_UUID = UUID("ABDD3056-28FA-441D-A470-55A75A52553A")


@dataclasses.dataclass
class DescrTestPeripheral:
    bleak_client: BleakClient
    bumble_peripheral: Device
    readable_descr: dict[UUID, Descriptor]
    writable_descr: dict[UUID, Descriptor]


STANDARD_DESCRIPTORS: list[tuple[UUID, bytes, bytes]] = [
    (
        gatt.GATT_CHARACTERISTIC_EXTENDED_PROPERTIES_DESCRIPTOR,
        b"\x03\x00",  # Reliable Write + Writable Auxiliaries
        b"\x01\x00",  # Only Reliable Write
    ),
    (
        gatt.GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
        "🚀 Description".encode(),  # Test Description
        "🔄 Updated".encode(),  # Alternative Description
    ),
    (
        gatt.GATT_CLIENT_CHARACTERISTIC_CONFIGURATION_DESCRIPTOR,
        b"\x01\x00",  # Notifications enabled
        b"\x02\x00",  # Indications enabled
    ),
    (
        gatt.GATT_SERVER_CHARACTERISTIC_CONFIGURATION_DESCRIPTOR,
        b"\x01\x00",  # Broadcasts enabled
        b"\x00\x00",  # Broadcasts disabled
    ),
    (
        gatt.GATT_CHARACTERISTIC_PRESENTATION_FORMAT_DESCRIPTOR,
        b"\x04\x00\xad\x27\x01\x00\x00",  # uint8, exponent 0, unit temperature celsius
        b"\x06\x00\x72\x27\x01\x00\x00",  # uint16, exponent 0, unit temperature celsius
    ),
    (
        gatt.GATT_CHARACTERISTIC_AGGREGATE_FORMAT_DESCRIPTOR,
        b"\x0a\x00\x0b\x00",  # Handles to two characteristics
        b"\x0c\x00\x0d\x00\x0e\x00",  # Handles to three characteristics
    ),
    (
        gatt.GATT_VALID_RANGE_DESCRIPTOR,
        b"\x00\x00\x64\x00",  # Min: 0, Max: 100
        b"\x0a\x00\x32\x00",  # Min: 10, Max: 50
    ),
    (
        gatt.GATT_EXTERNAL_REPORT_DESCRIPTOR,
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f",  # Example UUID
        b"\x0f\x0e\x0d\x0c\x0b\x0a\x09\x08\x07\x06\x05\x04\x03\x02\x01\x00",  # Different UUID
    ),
    (
        gatt.GATT_REPORT_REFERENCE_DESCRIPTOR,
        b"\x01\x01",  # Report ID: 1, Report Type: Input
        b"\x02\x02",  # Report ID: 2, Report Type: Output
    ),
    (
        gatt.GATT_NUMBER_OF_DIGITALS_DESCRIPTOR,
        b"\x08",  # 8 digital values
        b"\x10",  # 16 digital values
    ),
    (
        gatt.GATT_VALUE_TRIGGER_SETTING_DESCRIPTOR,
        b"\x01\x00\x00",  # Condition: None, value: 0
        b"\x02\x32\x00",  # Condition: different, value: 50
    ),
    (
        gatt.GATT_ENVIRONMENTAL_SENSING_CONFIGURATION_DESCRIPTOR,
        b"\x01",  # Trigger logic: OR
        b"\x02",  # Trigger logic: AND
    ),
    (
        gatt.GATT_ENVIRONMENTAL_SENSING_MEASUREMENT_DESCRIPTOR,
        b"\x01\x00\x00",  # Flags: 0x01, Sampling Function: Unspecified, Measurement Period: 0
        b"\x02\x01\x0a",  # Flags: 0x02, Sampling Function: Instantaneous, Measurement Period: 10
    ),
    (
        gatt.GATT_ENVIRONMENTAL_SENSING_TRIGGER_DESCRIPTOR,
        b"\x01\x00\x00",  # Flags: 0x01
        b"\x02\x00\x00",  # Flags: 0x02
    ),
    (
        gatt.GATT_TIME_TRIGGER_DESCRIPTOR,
        b"\x01\x00\x00",  # Condition: None, value: 0
        b"\x02\x3c\x00",  # Condition: different, value: 60
    ),
    (
        gatt.GATT_VALID_RANGE_AND_ACCURACY_DESCRIPTOR,
        b"\x00\x00\x64\x00\x01\x00",  # Min: 0, Max: 100, Accuracy: 1
        b"\x14\x00\x50\x00\x02\x00",  # Min: 20, Max: 80, Accuracy: 2
    ),
    (
        CUSTOM_BINARY_DESCRIPTOR_UUID,
        b"\x01\x02\x03\x04",  # Custom binary data
        b"\xaa\xbb\xcc\xdd",  # Different custom binary data
    ),
    (
        L2CAPPPSM_DESCRIPTOR_UUID,
        b"\x56\x30",  # PSM value 0x3056 in little-endian
        b"\x78\x40",  # PSM value 0x4078 in little-endian
    ),
]


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def descr_test_peripheral(
    bumble_peripheral: Device,
) -> AsyncGenerator[DescrTestPeripheral, None]:
    readable_descriptors = {
        descr_uuid: Descriptor(descr_uuid, Descriptor.READABLE, descr_data)
        for descr_uuid, descr_data, _ in STANDARD_DESCRIPTORS
    }

    readable_descr_char = Characteristic(
        READABLE_DESCR_CHAR_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"",
        list(readable_descriptors.values()),
    )

    writable_descr = {
        descr_uuid: Descriptor(descr_uuid, Descriptor.WRITEABLE, descr_data)
        for descr_uuid, descr_data, _ in STANDARD_DESCRIPTORS
    }
    writable_descr_char = Characteristic(
        WRITABLE_DESCR_CHAR_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"",
        list(writable_descr.values()),
    )

    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[
            Service(
                DESCR_TEST_SERVICE_UUID,
                [
                    readable_descr_char,
                    writable_descr_char,
                ],
            ),
        ],
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device, services=[DESCR_TEST_SERVICE_UUID]) as client:
        yield DescrTestPeripheral(
            bumble_peripheral=bumble_peripheral,
            bleak_client=client,
            readable_descr=readable_descriptors,
            writable_descr=writable_descr,
        )


@pytest.mark.parametrize(
    "descr_uuid,descr_data",
    [
        pytest.param(
            descr_uuid,
            descr_data,
            id=descr_uuid.to_hex_str(),
        )
        for descr_uuid, descr_data, _ in STANDARD_DESCRIPTORS
    ],
)
@pytest.mark.asyncio(loop_scope="module")
async def test_read_gatt_descriptor(
    descr_test_peripheral: DescrTestPeripheral,
    descr_uuid: UUID,
    descr_data: bytes,
):
    """
    Reading a string GATT descriptor is possible.

    On CoreBluetooth some descriptors are returned as NSString or NSNumber instead of NSData.
    This test ensures that all standard descriptors can be read correctly.
    """

    characteristic = descr_test_peripheral.bleak_client.services.get_characteristic(
        READABLE_DESCR_CHAR_UUID
    )
    assert characteristic

    descriptor = characteristic.get_descriptor(descr_uuid.to_hex_str())
    assert descriptor

    # Set data to a known value (other tests may have modified it)
    descr_test_peripheral.readable_descr[descr_uuid].value = descr_data

    data = await descr_test_peripheral.bleak_client.read_gatt_descriptor(descriptor)

    # Verify the data is as expected
    assert data == descr_data


@pytest.mark.asyncio(loop_scope="module")
async def test_read_gatt_descriptor_use_cached(
    descr_test_peripheral: DescrTestPeripheral,
):
    """Reading a cached GATT descriptor is possible."""
    characteristic = descr_test_peripheral.bleak_client.services.get_characteristic(
        READABLE_DESCR_CHAR_UUID
    )
    assert characteristic

    descriptor = characteristic.get_descriptor(
        gatt.GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR.to_hex_str()
    )
    assert descriptor

    bumble_descr = descr_test_peripheral.readable_descr[
        gatt.GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR
    ]

    # Set data to a known value (other tests may have modified it)
    bumble_descr.value = b"Original"

    data = await descr_test_peripheral.bleak_client.read_gatt_descriptor(descriptor)

    # Verify the data is as expected
    assert data == b"Original"

    # Change the value in the peripheral
    bumble_descr.value = b"Changed"

    data = await descr_test_peripheral.bleak_client.read_gatt_descriptor(
        descriptor, use_cached=True
    )

    # The data has to be the original value since we are using the cached value.
    assert data == b"Original"


@pytest.mark.parametrize(
    "descr_uuid,descr_data_1,descr_data_2",
    [
        pytest.param(
            descr_uuid,
            descr_data_1,
            descr_data_2,
            id=descr_uuid.to_hex_str(),
        )
        for descr_uuid, descr_data_1, descr_data_2 in STANDARD_DESCRIPTORS
    ],
)
@pytest.mark.asyncio(loop_scope="module")
async def test_write_gatt_descriptor(
    descr_test_peripheral: DescrTestPeripheral,
    descr_uuid: UUID,
    descr_data_1: bytes,
    descr_data_2: bytes,
):
    """Writing a GATT descriptor is possible."""

    characteristic = descr_test_peripheral.bleak_client.services.get_characteristic(
        WRITABLE_DESCR_CHAR_UUID
    )
    assert characteristic

    descriptor = characteristic.get_descriptor(descr_uuid.to_hex_str())
    assert descriptor

    # Set data to a known value
    descr_test_peripheral.writable_descr[descr_uuid].value = descr_data_1

    if descr_uuid == gatt.GATT_CLIENT_CHARACTERISTIC_CONFIGURATION_DESCRIPTOR:
        # writing CCCD should raise ValueError
        with pytest.raises(ValueError, match="Cannot write to CCCD"):
            await descr_test_peripheral.bleak_client.write_gatt_descriptor(
                descriptor, descr_data_2
            )
    else:
        await descr_test_peripheral.bleak_client.write_gatt_descriptor(
            descriptor, descr_data_2
        )

        # Verify the data is as expected
        assert descr_test_peripheral.writable_descr[descr_uuid].value == descr_data_2  # type: ignore  # (missing type hints in bumble)
