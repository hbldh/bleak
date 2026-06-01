"""Tests for the BlueZ pairing agent dispatch."""

import sys

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)
    assert False  # HACK: work around pyright bug

from unittest.mock import AsyncMock, MagicMock

from dbus_fast import DBusError

from bleak.backends.bluezdbus.agent import Agent, capability_name
from bleak.backends.device import BLEDevice
from bleak.pairing import (
    IOCapability,
    SupportsConfirm,
    SupportsDisplayPasskey,
    SupportsRequestPasskey,
)

_DEVICE_PATH = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"


@pytest.fixture(autouse=True)
def mock_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = MagicMock()
    manager.get_device_address.return_value = "AA:BB:CC:DD:EE:FF"
    manager.get_device_name.return_value = "Test Device"
    monkeypatch.setattr(
        "bleak.backends.bluezdbus.agent.get_global_bluez_manager",
        AsyncMock(return_value=manager),
    )


async def _confirm(agent: Agent, passkey: int = 123456) -> None:
    await agent._confirm(_DEVICE_PATH, passkey)  # pyright: ignore[reportPrivateUsage]


async def _request_passkey(agent: Agent) -> int:
    method = agent._request_passkey  # pyright: ignore[reportPrivateUsage]
    return await method(_DEVICE_PATH)


async def _display(agent: Agent, passkey: int = 123456) -> None:
    await agent._display(_DEVICE_PATH, passkey)  # pyright: ignore[reportPrivateUsage]


async def test_confirm_accepts() -> None:
    seen: list[int] = []

    class _Confirm(SupportsConfirm):
        async def confirm(self, device: BLEDevice, passkey: int) -> bool:
            seen.append(passkey)
            return True

    await _confirm(Agent(_Confirm()), 123456)

    assert seen == [123456]


async def test_confirm_rejected_raises() -> None:
    class _Confirm(SupportsConfirm):
        async def confirm(self, device: BLEDevice, passkey: int) -> bool:
            return False

    with pytest.raises(DBusError):
        await _confirm(Agent(_Confirm()))


async def test_confirm_without_callback_raises() -> None:
    with pytest.raises(DBusError):
        await _confirm(Agent(None))


async def test_request_passkey_returns_value() -> None:
    class _Request(SupportsRequestPasskey):
        async def request_passkey(self, device: BLEDevice) -> int | None:
            return 42

    assert await _request_passkey(Agent(_Request())) == 42


async def test_request_passkey_none_raises() -> None:
    class _Request(SupportsRequestPasskey):
        async def request_passkey(self, device: BLEDevice) -> int | None:
            return None

    with pytest.raises(DBusError):
        await _request_passkey(Agent(_Request()))


async def test_request_passkey_out_of_range_raises() -> None:
    class _Request(SupportsRequestPasskey):
        async def request_passkey(self, device: BLEDevice) -> int | None:
            return 1_000_000

    with pytest.raises(DBusError):
        await _request_passkey(Agent(_Request()))


async def test_request_passkey_without_callback_raises() -> None:
    with pytest.raises(DBusError):
        await _request_passkey(Agent(None))


async def test_display_invokes_callback() -> None:
    seen: list[int] = []

    class _Display(SupportsDisplayPasskey):
        async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
            seen.append(passkey)

    await _display(Agent(_Display()), 654321)

    assert seen == [654321]


async def test_display_without_callback_is_noop() -> None:
    await _display(Agent(None))


@pytest.mark.parametrize(
    ("capability", "name"),
    [
        (IOCapability.NO_INPUT_NO_OUTPUT, "NoInputNoOutput"),
        (IOCapability.DISPLAY_YES_NO, "DisplayYesNo"),
        (IOCapability.KEYBOARD_ONLY, "KeyboardOnly"),
        (IOCapability.DISPLAY_ONLY, "DisplayOnly"),
        (IOCapability.KEYBOARD_DISPLAY, "KeyboardDisplay"),
    ],
)
def test_capability_name(capability: IOCapability, name: str) -> None:
    assert capability_name(capability) == name
