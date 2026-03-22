import pytest

from bleak import BleakClient, BleakScanner


async def test_adapter_kwarg_deprecated_in_scanner():
    with pytest.deprecated_call(
        match="the 'adapter' keyword argument is deprecated, use the 'bluez' kwarg instead"
    ):
        BleakScanner(adapter="hci0")


async def test_adapter_kwarg_deprecated_in_client():
    with pytest.deprecated_call(
        match="the 'adapter' keyword argument is deprecated, use the 'bluez' kwarg instead"
    ):
        BleakClient("00:11:22:33:44:55", adapter="hci0")
