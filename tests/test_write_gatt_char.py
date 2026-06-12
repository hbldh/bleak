"""Tests for the data size check in BleakClient.write_gatt_char()."""

from typing import cast
from unittest.mock import Mock

import pytest

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection

TEST_CHARACTERISTIC_UUID = "797f54d7-83d1-49c7-9992-0d0b136117dd"


def create_client(backend: BaseBleakClient) -> BleakClient:
    """Create a BleakClient that uses the given (mock) backend instance."""
    backend.services = Mock(spec=BleakGATTServiceCollection)
    backend_type = Mock(return_value=backend)
    backend_type.__name__ = "MockBleakClientBackend"
    return BleakClient(
        "00:11:22:33:44:55", backend=cast(type[BaseBleakClient], backend_type)
    )


def create_characteristic(
    max_write_without_response_size: int,
) -> BleakGATTCharacteristic:
    """Create a characteristic with the given write-without-response limit."""
    return BleakGATTCharacteristic(
        None,
        1,
        TEST_CHARACTERISTIC_UUID,
        ["write-without-response"],
        lambda: max_write_without_response_size,
        cast(BleakGATTService, Mock(spec=BleakGATTService)),
    )


async def test_write_without_response_too_large_raises() -> None:
    """Writing more data than the known limit allows raises ValueError."""
    backend = Mock(spec=BaseBleakClient)
    client = create_client(backend)
    characteristic = create_characteristic(100)

    with pytest.raises(ValueError, match="write without response"):
        await client.write_gatt_char(characteristic, bytes(101), response=False)

    backend.write_gatt_char.assert_not_called()


async def test_write_without_response_within_limit() -> None:
    """Writing data up to the known limit is passed to the backend."""
    backend = Mock(spec=BaseBleakClient)
    client = create_client(backend)
    characteristic = create_characteristic(100)

    await client.write_gatt_char(characteristic, bytes(100), response=False)

    backend.write_gatt_char.assert_awaited_once_with(characteristic, bytes(100), False)


async def test_write_with_response_limit_not_enforced() -> None:
    """The limit only applies to write without response."""
    backend = Mock(spec=BaseBleakClient)
    client = create_client(backend)
    characteristic = create_characteristic(100)

    await client.write_gatt_char(characteristic, bytes(101), response=True)

    backend.write_gatt_char.assert_awaited_once_with(characteristic, bytes(101), True)


async def test_write_without_response_unknown_limit_not_enforced() -> None:
    """
    A limit of 20 may just be a fallback for when the actual limit is not
    known, so oversized writes are passed to the backend in that case.
    """
    backend = Mock(spec=BaseBleakClient)
    client = create_client(backend)
    characteristic = create_characteristic(20)

    await client.write_gatt_char(characteristic, bytes(100), response=False)

    backend.write_gatt_char.assert_awaited_once_with(characteristic, bytes(100), False)
