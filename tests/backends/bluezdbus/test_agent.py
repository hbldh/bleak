"""Tests for the BlueZ pairing agent dispatch."""

import sys

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)
    assert False  # HACK: work around pyright bug

from unittest.mock import AsyncMock, MagicMock

from dbus_fast import DBusError

from bleak.agent import (
    ConfirmPasskey,
    DisplayPasskey,
    IOCapability,
    PairingCallbacks,
    RequestPasskey,
)
from bleak.backends.bluezdbus.agent import (
    _capability_name,  # pyright: ignore[reportPrivateUsage]
)
from bleak.backends.bluezdbus.agent import Agent

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

    async def confirm(request: ConfirmPasskey) -> bool:
        seen.append(request.passkey)
        return True

    await _confirm(Agent(PairingCallbacks(confirm=confirm)), 123456)

    assert seen == [123456]


async def test_confirm_rejected_raises() -> None:
    async def confirm(request: ConfirmPasskey) -> bool:
        return False

    with pytest.raises(DBusError):
        await _confirm(Agent(PairingCallbacks(confirm=confirm)))


async def test_confirm_without_callback_raises() -> None:
    with pytest.raises(DBusError):
        await _confirm(Agent(PairingCallbacks()))


async def test_request_passkey_returns_value() -> None:
    async def request_passkey(request: RequestPasskey) -> int | None:
        return 42

    assert (
        await _request_passkey(Agent(PairingCallbacks(request_passkey=request_passkey)))
        == 42
    )


async def test_request_passkey_none_raises() -> None:
    async def request_passkey(request: RequestPasskey) -> int | None:
        return None

    with pytest.raises(DBusError):
        await _request_passkey(Agent(PairingCallbacks(request_passkey=request_passkey)))


async def test_request_passkey_out_of_range_raises() -> None:
    async def request_passkey(request: RequestPasskey) -> int | None:
        return 1_000_000

    with pytest.raises(DBusError):
        await _request_passkey(Agent(PairingCallbacks(request_passkey=request_passkey)))


async def test_request_passkey_without_callback_raises() -> None:
    with pytest.raises(DBusError):
        await _request_passkey(Agent(PairingCallbacks()))


async def test_display_invokes_callback() -> None:
    seen: list[int] = []

    async def display_passkey(request: DisplayPasskey) -> None:
        seen.append(request.passkey)

    await _display(Agent(PairingCallbacks(display_passkey=display_passkey)), 654321)

    assert seen == [654321]


async def test_display_without_callback_is_noop() -> None:
    await _display(Agent(PairingCallbacks()))


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
    assert _capability_name(capability) == name
