import asyncio
import logging
from collections.abc import AsyncGenerator

import pytest
from bumble.device import Connection, Device
from bumble.pairing import PairingConfig, PairingDelegate

from bleak import BleakClient
from bleak.agent import ConfirmPasskey, DisplayPasskey, PairingCallbacks, RequestPasskey
from bleak.backends import BleakBackend, get_default_backend
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)

logger = logging.getLogger(__name__)

_PAIRING_BACKENDS = (BleakBackend.WIN_RT, BleakBackend.BLUEZ_DBUS)

pairing_supported = pytest.mark.skipif(
    get_default_backend() not in _PAIRING_BACKENDS,
    reason="pairing with callbacks is only implemented on WinRT and BlueZ",
)


@pytest.fixture
async def pairing_peripheral(bumble_peripheral: Device) -> AsyncGenerator[Device, None]:
    """Wrap :func:`bumble_peripheral` with the teardown a pairing test needs.

    A successful pairing leaves an OS-level bond and a still-powered-on bumble
    device. A leaked bond makes the next SMP exchange fail, so the bond is
    removed here. Each teardown step is isolated because a single bumble
    cleanup failure can otherwise leave the controller hung.
    """
    try:
        yield bumble_peripheral
    finally:
        address = str(bumble_peripheral.random_address)
        try:
            await BleakClient(address).unpair()
        except Exception as e:
            logger.warning("teardown unpair of %s failed: %s", address, e)
        try:
            await bumble_peripheral.power_off()
        except Exception as e:
            logger.warning("teardown power_off failed: %s", e)


class _JustWorksDelegate(PairingDelegate):
    """Peripheral side of a Just Works (no MITM) pairing."""

    def __init__(self) -> None:
        super().__init__(io_capability=PairingDelegate.NO_OUTPUT_NO_INPUT)


class _DisplayDelegate(PairingDelegate):
    """Peripheral displays the passkey; the central enters it."""

    def __init__(self, displayed: "asyncio.Future[int]") -> None:
        super().__init__(io_capability=PairingDelegate.DISPLAY_OUTPUT_ONLY)
        self._displayed = displayed

    async def display_number(self, number: int, digits: int) -> None:
        if not self._displayed.done():
            self._displayed.set_result(number)


class _KeyboardDelegate(PairingDelegate):
    """Peripheral enters the passkey the central displays."""

    def __init__(self, displayed: "asyncio.Future[int]") -> None:
        super().__init__(io_capability=PairingDelegate.KEYBOARD_INPUT_ONLY)
        self._displayed = displayed

    async def get_number(self) -> int | None:
        return await self._displayed


class _CompareDelegate(PairingDelegate):
    """Peripheral confirms a numeric comparison; records the shown passkey."""

    def __init__(self, shown: "asyncio.Future[int]") -> None:
        super().__init__(io_capability=PairingDelegate.DISPLAY_OUTPUT_AND_YES_NO_INPUT)
        self._shown = shown

    async def compare_numbers(self, number: int, digits: int) -> bool:
        if not self._shown.done():
            self._shown.set_result(number)
        return True


def _use_pairing(peripheral: Device, delegate: PairingDelegate, *, mitm: bool) -> None:
    def factory(_connection: Connection) -> PairingConfig:
        return PairingConfig(sc=True, mitm=mitm, bonding=True, delegate=delegate)

    peripheral.pairing_config_factory = factory


@pairing_supported
async def test_pair_just_works(pairing_peripheral: Device) -> None:
    """Just Works pairing succeeds with no callbacks."""
    _use_pairing(pairing_peripheral, _JustWorksDelegate(), mitm=False)
    await configure_and_power_on_bumble_peripheral(pairing_peripheral)
    device = await find_ble_device(pairing_peripheral)

    async with BleakClient(device, pair=True) as client:
        assert client.is_connected


@pairing_supported
async def test_pair_numeric_comparison(pairing_peripheral: Device) -> None:
    """Numeric Comparison: both sides see the same passkey and accept."""
    loop = asyncio.get_running_loop()
    peripheral_passkey: "asyncio.Future[int]" = loop.create_future()
    central_passkey: "asyncio.Future[int]" = loop.create_future()

    _use_pairing(pairing_peripheral, _CompareDelegate(peripheral_passkey), mitm=True)
    await configure_and_power_on_bumble_peripheral(pairing_peripheral)
    device = await find_ble_device(pairing_peripheral)

    async def confirm(request: ConfirmPasskey) -> bool:
        if not central_passkey.done():
            central_passkey.set_result(request.passkey)
        return True

    async with BleakClient(
        device, pairing_callbacks=PairingCallbacks(confirm=confirm), pair=True
    ) as client:
        assert client.is_connected

    assert await peripheral_passkey == await central_passkey


@pairing_supported
async def test_pair_passkey_entry_central_inputs(pairing_peripheral: Device) -> None:
    """Passkey Entry where the peripheral displays and the central enters."""
    loop = asyncio.get_running_loop()
    displayed: "asyncio.Future[int]" = loop.create_future()

    _use_pairing(pairing_peripheral, _DisplayDelegate(displayed), mitm=True)
    await configure_and_power_on_bumble_peripheral(pairing_peripheral)
    device = await find_ble_device(pairing_peripheral)

    async def request_passkey(request: RequestPasskey) -> int | None:
        return await displayed

    async with BleakClient(
        device,
        pairing_callbacks=PairingCallbacks(request_passkey=request_passkey),
        pair=True,
    ) as client:
        assert client.is_connected


@pairing_supported
async def test_pair_passkey_entry_central_displays(pairing_peripheral: Device) -> None:
    """Passkey Entry where the central displays and the peripheral enters."""
    loop = asyncio.get_running_loop()
    displayed: "asyncio.Future[int]" = loop.create_future()

    _use_pairing(pairing_peripheral, _KeyboardDelegate(displayed), mitm=True)
    await configure_and_power_on_bumble_peripheral(pairing_peripheral)
    device = await find_ble_device(pairing_peripheral)

    async def display_passkey(request: DisplayPasskey) -> None:
        if not displayed.done():
            displayed.set_result(request.passkey)

    async with BleakClient(
        device,
        pairing_callbacks=PairingCallbacks(display_passkey=display_passkey),
        pair=True,
    ) as client:
        assert client.is_connected


@pairing_supported
async def test_unpair(pairing_peripheral: Device) -> None:
    """Pair then unpair a device.

    Smoke test: there is no portable way to assert the OS bond was actually
    removed, so this only verifies that ``unpair()`` completes without raising.
    """
    _use_pairing(pairing_peripheral, _JustWorksDelegate(), mitm=False)
    await configure_and_power_on_bumble_peripheral(pairing_peripheral)
    device = await find_ble_device(pairing_peripheral)

    client = BleakClient(device, pair=True)
    await client.connect()
    await client.disconnect()
    await client.unpair()


@pytest.mark.skipif(
    get_default_backend() != BleakBackend.CORE_BLUETOOTH,
    reason="pairing is not possible on CoreBluetooth",
)
async def test_pairing_unavailable(bumble_peripheral: Device) -> None:
    """Check if pairing on CoreBluetooth raises an error."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    client = BleakClient(device)
    with pytest.raises(NotImplementedError):
        await client.pair()
    with pytest.raises(NotImplementedError):
        await client.unpair()
