import dataclasses
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from bumble.device import Device
from bumble.gatt import (
    GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
    Characteristic,
    Descriptor,
    Service,
)
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


@dataclasses.dataclass
class DescrTestPeripheral:
    bleak_client: BleakClient
    bumble_peripheral: Device
    readable_descr: Descriptor
    writable_descr: Descriptor


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def descr_test_peripheral(
    bumble_peripheral: Device,
) -> AsyncGenerator[DescrTestPeripheral, None]:

    readable_descr = Descriptor(
        GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
        Descriptor.READABLE,
        "Description".encode(),
    )
    readable_descr_char = Characteristic(
        READABLE_DESCR_CHAR_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"",
        [readable_descr],
    )

    writable_descr = Descriptor(
        GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
        Descriptor.WRITEABLE,
        b"-----------",
    )
    writable_descr_char = Characteristic(
        WRITABLE_DESCR_CHAR_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"",
        [writable_descr],
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
            readable_descr=readable_descr,
            writable_descr=writable_descr,
        )


@pytest.mark.asyncio(loop_scope="module")
async def test_read_gatt_descriptor(descr_test_peripheral: DescrTestPeripheral):
    """Reading a GATT descriptor is possible."""

    characteristic = descr_test_peripheral.bleak_client.services.get_characteristic(
        READABLE_DESCR_CHAR_UUID
    )
    assert characteristic

    descriptor = characteristic.get_descriptor(
        GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR.to_hex_str()
    )
    assert descriptor

    descr_test_peripheral.readable_descr.value = b"Description"
    data = await descr_test_peripheral.bleak_client.read_gatt_descriptor(descriptor)
    assert data == b"Description"


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
        GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR.to_hex_str()
    )
    assert descriptor

    descr_test_peripheral.readable_descr.value = b"Original"
    data = await descr_test_peripheral.bleak_client.read_gatt_descriptor(descriptor)
    assert data == b"Original"

    descr_test_peripheral.readable_descr.value = b"Changed"
    data = await descr_test_peripheral.bleak_client.read_gatt_descriptor(
        descriptor, use_cached=True
    )

    # The data has to be the old value since we are using the cached value.
    assert data == b"Original"


@pytest.mark.asyncio(loop_scope="module")
async def test_write_gatt_descriptor(descr_test_peripheral: DescrTestPeripheral):
    """Writing a GATT descriptor is possible."""

    characteristic = descr_test_peripheral.bleak_client.services.get_characteristic(
        WRITABLE_DESCR_CHAR_UUID
    )
    assert characteristic

    descriptor = characteristic.get_descriptor(
        GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR.to_hex_str()
    )
    assert descriptor

    descr_test_peripheral.writable_descr.value = b"Original"

    await descr_test_peripheral.bleak_client.write_gatt_descriptor(
        descriptor, b"Changed"
    )
    assert descr_test_peripheral.writable_descr.value == b"Changed"  # type: ignore  # (missing type hints in bumble)
