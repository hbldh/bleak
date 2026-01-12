import asyncio
import dataclasses
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from bumble.att import ATT_Error, ErrorCode
from bumble.device import Connection, Device
from bumble.gatt import Characteristic, CharacteristicValue, Service
from bumble.transport.common import Transport

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakGATTProtocolError
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


CHAR_TEST_SERVICE_UUID = "2908f536-3fab-43c9-a7b2-80b6fdaae99b"

READ_CHAR_UUID = "1a1af049-9c23-4b69-b763-e1096674ed18"
WRITE_WITH_RESPONSE_CHAR_UUID = "79a92bad-31b4-4a70-885c-e704ae2c6363"
WRITE_WITHOUT_RESPONSE_CHAR_UUID = "2a07f6ea-6401-45d7-838c-0f459a7edb7f"
NOTIFY_CHAR_UUID = "d4c6dad3-76f1-4034-8871-0a6345be6cfc"


@dataclasses.dataclass
class CharTestPeripheral:
    bleak_client: BleakClient
    bumble_peripheral: Device
    read_characteristic: Characteristic[bytes]
    write_characteristic: Characteristic[bytes]
    write_without_response_characteristic: Characteristic[bytes]
    notify_characteristic: Characteristic[bytes]


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def char_test_peripheral(
    bumble_peripheral: Device,
) -> AsyncGenerator[CharTestPeripheral, None]:
    read_characteristic = Characteristic[bytes](
        READ_CHAR_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"DATA",
    )
    write_characteristic = Characteristic[bytes](
        WRITE_WITH_RESPONSE_CHAR_UUID,
        Characteristic.Properties.WRITE,
        Characteristic.WRITEABLE,
        b"----",
    )
    write_without_response_characteristic = Characteristic[bytes](
        WRITE_WITHOUT_RESPONSE_CHAR_UUID,
        Characteristic.Properties.WRITE_WITHOUT_RESPONSE,
        Characteristic.WRITEABLE,
        None,
    )
    notify_characteristic = Characteristic[bytes](
        NOTIFY_CHAR_UUID,
        Characteristic.Properties.READ | Characteristic.Properties.NOTIFY,
        Characteristic.Permissions.READABLE,
        b"----",
    )

    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[
            Service(
                CHAR_TEST_SERVICE_UUID,
                [
                    read_characteristic,
                    write_characteristic,
                    write_without_response_characteristic,
                    notify_characteristic,
                ],
            ),
        ],
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(device, services=[CHAR_TEST_SERVICE_UUID]) as client:
        yield CharTestPeripheral(
            bumble_peripheral=bumble_peripheral,
            bleak_client=client,
            read_characteristic=read_characteristic,
            write_characteristic=write_characteristic,
            write_without_response_characteristic=write_without_response_characteristic,
            notify_characteristic=notify_characteristic,
        )


GATT_ERRORS = [
    # These error codes are explicitly called out as possible errors from
    # ATT_WRITE_REQ in the Bluetooth Core Specification. Commented-out codes
    # are not possible to test, e.g. causes BlueZ to disconnect rather than
    # return an error.
    ErrorCode.INVALID_ATTRIBUTE_LENGTH,
    ErrorCode.INSUFFICIENT_AUTHORIZATION,
    # ErrorCode.INSUFFICIENT_AUTHENTICATION,
    # ErrorCode.INSUFFICIENT_ENCRYPTION_KEY_SIZE,
    # ErrorCode.INSUFFICIENT_ENCRYPTION,
    ErrorCode.INVALID_HANDLE,
    #
    # Then these are specifically handled by BlueZ, so assumed to be
    # possible in the wild. INVALID_OFFSET seems to trigger .InvalidArgs
    # which is the same as INVALID_ATTRIBUTE_LENGTH, so not tested here.
    ErrorCode.REQUEST_NOT_SUPPORTED,
    # ErrorCode.INVALID_OFFSET,
    ErrorCode.CCCD_IMPROPERLY_CONFIGURED,
    #
    # And allows custom error codes from higher layers.
    ErrorCode(0xC0),  # Application Error
    ErrorCode(0xE0),  # Common Profile or Service Error Codes
]

GATT_READ_ERRORS = GATT_ERRORS + [ErrorCode.READ_NOT_PERMITTED]
GATT_WRITE_ERRORS = GATT_ERRORS + [ErrorCode.WRITE_NOT_PERMITTED]


@pytest.mark.asyncio(loop_scope="module")
async def test_read_gatt_char(
    char_test_peripheral: CharTestPeripheral,
):
    """Reading a GATT characteristic is possible."""

    # Set data to a known value
    char_test_peripheral.read_characteristic.value = b"DATA"
    data = await char_test_peripheral.bleak_client.read_gatt_char(READ_CHAR_UUID)

    # Verify the data is as expected
    assert data == b"DATA"


@pytest.mark.asyncio(loop_scope="module")
async def test_read_gatt_char_use_cached(char_test_peripheral: CharTestPeripheral):
    """Reading a cached GATT characteristic is possible."""

    # Set data to a known value
    char_test_peripheral.read_characteristic.value = b"ORIGINAL"
    await char_test_peripheral.bleak_client.read_gatt_char(READ_CHAR_UUID)

    # Change the data to a different value
    char_test_peripheral.read_characteristic.value = b"CHANGED"

    data = await char_test_peripheral.bleak_client.read_gatt_char(
        READ_CHAR_UUID, use_cached=True
    )

    # The data has to be the old value since we are using the cached value.
    assert data == b"ORIGINAL"


@pytest.mark.parametrize("gatt_error", GATT_READ_ERRORS)
@pytest.mark.asyncio(loop_scope="module")
async def test_read_gatt_char_error(
    char_test_peripheral: CharTestPeripheral, gatt_error: ErrorCode
):
    """
    Reading a GATT characteristic passes back GATT errors correctly.
    """

    # TODO: should add a test option to allow not skipping if user is available
    # to click through any permission prompts.
    if sys.platform == "darwin" and gatt_error == ErrorCode.INSUFFICIENT_AUTHORIZATION:
        pytest.skip(
            "Apple asks for user permission via a prompt, which cannot be handled automatically."
        )

    def error_on_read(connection: Connection) -> bytes:
        raise ATT_Error(gatt_error)

    char_test_peripheral.read_characteristic.value = CharacteristicValue(
        read=error_on_read
    )

    with pytest.raises(BleakGATTProtocolError) as exc_info:
        await char_test_peripheral.bleak_client.read_gatt_char(READ_CHAR_UUID)

    assert exc_info.value.code == gatt_error


@pytest.mark.asyncio(loop_scope="module")
async def test_write_gatt_char_with_response(char_test_peripheral: CharTestPeripheral):
    """Writing a GATT characteristic is possible."""

    # Set data to a known value
    char_test_peripheral.write_characteristic.value = b"----"

    await char_test_peripheral.bleak_client.write_gatt_char(
        WRITE_WITH_RESPONSE_CHAR_UUID, b"DATA", response=True
    )

    # Verify the new data was written correctly
    assert char_test_peripheral.write_characteristic.value == b"DATA"


@pytest.mark.parametrize("gatt_error", GATT_WRITE_ERRORS)
@pytest.mark.asyncio(loop_scope="module")
async def test_write_gatt_char_with_response_error(
    char_test_peripheral: CharTestPeripheral, gatt_error: ErrorCode
):
    """
    Writing a GATT characteristic propagates error codes correctly.
    """

    # TODO: should add a test option to allow not skipping if user is available
    # to click through any permission prompts.
    if sys.platform == "darwin" and gatt_error == ErrorCode.INSUFFICIENT_AUTHORIZATION:
        pytest.skip(
            "Apple asks for user permission via a prompt, which cannot be handled automatically."
        )

    def error_on_write(connection: Connection, value: bytes):
        raise ATT_Error(gatt_error)

    char_test_peripheral.write_characteristic.value = CharacteristicValue(
        write=error_on_write
    )

    with pytest.raises(BleakGATTProtocolError) as exc_info:
        await char_test_peripheral.bleak_client.write_gatt_char(
            WRITE_WITH_RESPONSE_CHAR_UUID, b"DATA", response=True
        )

    assert exc_info.value.code == gatt_error


@pytest.mark.asyncio(loop_scope="module")
async def test_write_gatt_char_no_response(char_test_peripheral: CharTestPeripheral):
    """Writing a GATT characteristic is possible."""
    peripheral_write_callback_called: asyncio.Future[bytes] = asyncio.Future()

    def peripheral_write_callback(connection: Connection, value: bytes):
        peripheral_write_callback_called.set_result(value)

    char_test_peripheral.write_without_response_characteristic.value = (
        CharacteristicValue(write=peripheral_write_callback)
    )

    await char_test_peripheral.bleak_client.write_gatt_char(
        WRITE_WITHOUT_RESPONSE_CHAR_UUID, b"DATA", response=False
    )
    written_value = await asyncio.wait_for(peripheral_write_callback_called, timeout=1)
    assert written_value == b"DATA"


@pytest.mark.asyncio(loop_scope="module")
async def test_notify_gatt_char(char_test_peripheral: CharTestPeripheral):
    """Writing a GATT characteristic is possible."""

    notified_data: asyncio.Queue[bytes] = asyncio.Queue()

    def notify_callback(characteristic: BleakGATTCharacteristic, data: bytearray):
        assert characteristic.uuid.lower() == NOTIFY_CHAR_UUID
        notified_data.put_nowait(bytes(data))

    await char_test_peripheral.bleak_client.start_notify(
        NOTIFY_CHAR_UUID,
        notify_callback,
    )
    assert notified_data.empty()

    await char_test_peripheral.bumble_peripheral.notify_subscribers(  # type: ignore  # (missing type hints in bumble)
        char_test_peripheral.notify_characteristic,
        b"1234",
    )

    data = await asyncio.wait_for(notified_data.get(), timeout=1)
    assert data == b"1234"

    await char_test_peripheral.bumble_peripheral.notify_subscribers(  # type: ignore  # (missing type hints in bumble)
        char_test_peripheral.notify_characteristic,
        b"2345",
    )

    data = await asyncio.wait_for(notified_data.get(), timeout=1)
    assert data == b"2345"

    await char_test_peripheral.bleak_client.stop_notify(NOTIFY_CHAR_UUID)

    await char_test_peripheral.bumble_peripheral.notify_subscribers(  # type: ignore  # (missing type hints in bumble)
        char_test_peripheral.notify_characteristic,
        b"2345",
    )

    # Verify no notification was received
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(notified_data.get(), timeout=1)
